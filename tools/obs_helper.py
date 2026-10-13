#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立 OBS Helper：本机 Named Pipe 生命周期快照 → OBS WebSocket 5。"""
from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import threading
import time
import uuid

# 随发行包附带的 WebSocket 实现优先；不自行实现 WebSocket 帧协议。
sys.path.insert(0, str(Path(__file__).resolve().parent / "obs_runtime"))
PIPE_NAME = r"\\.\pipe\DivaKaraokeObsV1"


class ObsClient:
    """只实现 OBS 官方 v5 的认证和请求包装，传输由 websocket-client 提供。"""

    # 初始化连接参数；密码不落日志，不通过游戏 IPC 传输。
    def __init__(self, host="127.0.0.1", port=4455, password=""):
        self.host, self.port, self.password = host, port, password
        self.socket = None
        self.stop_generation = 0

    # 根据官方双 SHA-256 + Base64 规则生成认证字段。
    @staticmethod
    def authentication(password, salt, challenge):
        secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
        return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()

    # 连接本机 OBS 并订阅录制状态事件，保留人工停止/重启的所有权边界。
    def connect(self):
        import websocket
        address = f"[{self.host}]" if ":" in self.host else self.host
        self.socket = websocket.create_connection(
            f"ws://{address}:{self.port}", timeout=1.0, http_proxy_host=None,
            http_no_proxy=[self.host], enable_multithread=True)
        try:
            hello = json.loads(self.socket.recv())
            if hello.get("op") != 0:
                raise RuntimeError("OBS 握手消息不正确")
            identify = {"rpcVersion": 1, "eventSubscriptions": 64}
            auth = hello["d"].get("authentication")
            if auth:
                identify["authentication"] = self.authentication(self.password, auth["salt"], auth["challenge"])
            self.socket.send(json.dumps({"op": 1, "d": identify}))
            if json.loads(self.socket.recv()).get("op") != 2:
                raise RuntimeError("OBS 认证未完成")
        except Exception:
            self.close()
            raise RuntimeError("OBS 连接或认证失败，请检查端口和密码") from None

    # 收集录制停止事件；人工重新录制后，不沿用上一次所有权。
    def handle_event(self, packet):
        data = packet.get("d", {})
        if packet.get("op") == 5 and data.get("eventType") == "RecordStateChanged":
            state = data.get("eventData", {}).get("outputState", "")
            if state in ("OBS_WEBSOCKET_OUTPUT_STOPPING", "OBS_WEBSOCKET_OUTPUT_STOPPED"):
                self.stop_generation += 1

    # 使用唯一请求编号匹配响应；超时关闭连接，防止迟到响应污染下一次请求。
    def request(self, kind, request_data=None):
        if self.socket is None:
            self.connect()
        request_id = uuid.uuid4().hex
        try:
            self.socket.settimeout(15 if kind == "StopRecord" else 3)
            data = {"requestType": kind, "requestId": request_id}
            if request_data is not None:
                data["requestData"] = request_data
            self.socket.send(json.dumps({"op": 6, "d": data}, ensure_ascii=False))
            # 停止需等待封装完成，后台管道可超时但不会重复发出启动请求。
            deadline = time.monotonic() + (15 if kind == "StopRecord" else 3)
            while time.monotonic() < deadline:
                packet = json.loads(self.socket.recv())
                self.handle_event(packet)
                if packet.get("op") == 7 and packet.get("d", {}).get("requestId") == request_id:
                    data = packet["d"]
                    if not data.get("requestStatus", {}).get("result"):
                        code = data.get("requestStatus", {}).get("code", 0)
                        raise RuntimeError(f"OBS 拒绝请求，错误编号 {code}")
                    return data.get("responseData", {})
            raise RuntimeError("OBS 响应超时")
        except Exception:
            self.close()
            raise RuntimeError("OBS 请求失败或超时；不会重试启动录制") from None

    # 关闭网络连接；重连后不自动认领未知录制。
    def close(self):
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
        self.socket = None


# 清理 Windows 文件名并禁止 OBS 把曲名中的百分号当作日期模板。
def safe_recording_stem(title, pvid, non_vocal):
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", str(title)).replace("%", "％").strip(" .")
    # 按 UTF-16 单位限制长度，给扩展名、序号和目录留下空间。
    title = title.encode("utf-16-le")[:200].decode("utf-16-le", errors="ignore").rstrip(" .")
    if not title:
        title = f"PV{pvid:03d}"
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?", title):
        title = "_" + title
    return f"{title}-{'Off Vocal' if non_vocal else 'On Vocal'}"


class RecordingController:
    """只控制成功 StartRecord 的本会话；失败、丢响应、重连均不猜测所有权。"""

    # 初始化去重记录、录制所有权和异常退出看门狗。
    def __init__(self, client, clock=time.monotonic, recovery_path=None, log_path=None):
        self.client, self.clock = client, clock
        self.owner = None
        self.owner_generation = None
        self.current = None
        self.attempted = None
        self.last_heartbeat = None
        self.test_counter = None
        self.status = "Helper 就绪；等待游戏连接"
        self.lock = threading.RLock()
        # 恢复日志仅保存文件名模板和配置名，不保存 OBS 密码。
        self.recovery_path = recovery_path
        self.log_path = log_path
        self.template_backup = None
        self.reserved = set()
        self.saved_outputs = []
        if recovery_path is not None and recovery_path.exists():
            try:
                self.template_backup = json.loads(recovery_path.read_text(encoding="utf-8"))
            except Exception:
                raise RuntimeError("OBS 文件名恢复记录损坏，请先检查 obs-filename-recovery.json") from None

    # 日志记录每首的真实保存路径，方便核对连续两首及实际输出结果。
    def log(self, message):
        if self.log_path is not None:
            try:
                with self.log_path.open("a", encoding="utf-8") as output:
                    output.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
            except OSError:
                self.status += "；日志写入失败"

    # 使用 OBS 官方配置请求包装，删除原本不存在的值时传入空值。
    def set_template(self, value):
        self.client.request("SetProfileParameter", {"parameterCategory": "Output",
            "parameterName": "FilenameFormatting", "parameterValue": value})

    # 模板恢复必须针对同一配置；用户手动修改的模板不覆盖。
    def restore_template(self):
        if self.template_backup is None:
            return True
        try:
            backup = self.template_backup
            profile = self.client.request("GetProfileList")["currentProfileName"]
            if profile != backup["profile"]:
                self.status = "OBS 已切换配置；等待回到原配置后恢复文件名模板"
                return False
            current = self.client.request("GetProfileParameter", {"parameterCategory": "Output",
                "parameterName": "FilenameFormatting"}).get("parameterValue")
            if current == backup["temporary"]:
                self.set_template(backup["original"])
            if self.recovery_path is not None:
                self.recovery_path.unlink(missing_ok=True)
            self.template_backup = None
            return True
        except Exception:
            self.status = "OBS 文件名模板恢复待处理；重连后继续恢复"
            return False

    # 同名使用递增序号，检查所有扩展名并保留本进程已使用名称。
    def prepare_filename(self, title, pvid, non_vocal):
        directory = Path(self.client.request("GetRecordDirectory")["recordDirectory"])
        existing = {path.stem.casefold() for path in directory.iterdir() if path.is_file()}
        stem = safe_recording_stem(title, pvid, non_vocal)
        candidate, number = stem, 1
        while candidate.casefold() in existing or (str(directory).casefold(), candidate.casefold()) in self.reserved:
            number += 1
            candidate = f"{stem} ({number})"
        profile = self.client.request("GetProfileList")["currentProfileName"]
        original = self.client.request("GetProfileParameter", {"parameterCategory": "Output",
            "parameterName": "FilenameFormatting"}).get("parameterValue")
        self.template_backup = {"profile": profile, "original": original, "temporary": candidate}
        # 必须先持久化再修改 OBS，Helper 异常退出后仍可恢复。
        if self.recovery_path is not None:
            self.recovery_path.write_text(json.dumps(self.template_backup, ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_template(candidate)
        self.reserved.add((str(directory).casefold(), candidate.casefold()))
        return candidate

    # 查询录制状态并撤销用户已经停止的旧会话所有权。
    def record_status(self):
        was_connected = self.client.socket is not None
        result = self.client.request("GetRecordStatus")
        if self.owner is not None and (not was_connected or
                self.client.stop_generation != self.owner_generation or not result.get("outputActive")):
            self.owner = None
            self.owner_generation = None
            self.restore_template()
        return result

    # 仅在连接连续、未发生停止事件且本功能仍拥有当前录制时停止。
    def stop_owned(self):
        if self.owner is None:
            return
        try:
            result = self.record_status()
            if self.owner is not None and result.get("outputActive"):
                saved = self.client.request("StopRecord").get("outputPath", "")
                self.status = "录制已停止，继续待命" + (f"；文件：{saved}" if saved else "；OBS 未返回保存路径，需检查")
                if saved:
                    self.saved_outputs.append(saved)
                self.log(self.status)
                # StopRecord 返回路径早于输出完全停止，必须等封装收尾再启动下一首。
                deadline = time.monotonic() + 15
                while self.client.request("GetRecordStatus").get("outputActive"):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("OBS 停止封装尚未完成")
                    time.sleep(0.05)
        except Exception:
            self.status = "OBS 已断开；录制所有权已释放，请在 OBS 检查录制"
        finally:
            self.owner = None
            self.owner_generation = None
            self.restore_template()

    # 接受一份快照；暂停时 active 保持真，不停止也不重复开始。
    def process(self, pid, epoch, enabled, active, pvid, test_counter, title="", non_vocal=False):
        with self.lock:
            token = (pid, epoch, pvid)
            self.last_heartbeat = self.clock()
            if token != self.current:
                self.stop_owned()
                self.current = token
                self.attempted = None
            if self.test_counter != (pid, test_counter):
                self.test_counter = (pid, test_counter)
                if test_counter:
                    try:
                        self.record_status()
                        self.status = "OBS 已连接，认证成功"
                    except Exception:
                        self.status = "OBS 连接失败，请检查 OBS WebSocket 服务和 Helper 密码"
            if not enabled or not active:
                self.stop_owned()
                self.restore_template()
                return self.status
            if self.attempted == token:
                # 断联或未知录像释放所有权后，心跳仍继续恢复模板，但不重启或停止录像。
                if self.owner is None and self.template_backup is not None:
                    self.restore_template()
                if self.owner:
                    try:
                        self.record_status()
                        if not self.owner:
                            self.status = "录制已由用户停止或重启；本 PV 不再干预"
                    except Exception:
                        self.owner = None
                        self.status = "OBS 断线；不重启本 PV 录制，请在 OBS 检查"
                return self.status
            # 先标记尝试，StartRecord 丢响应时本会话绝不重复尝试或停止未知录制。
            self.attempted = token
            try:
                if not self.restore_template():
                    return self.status
                if self.record_status().get("outputActive"):
                    self.status = "OBS 已有人工录制；本 PV 跳过自动录制"
                    return self.status
                filename = self.prepare_filename(title, pvid, non_vocal)
                # 修改模板后再次核对，避免配置请求期间人工启动的录像被认领。
                if self.record_status().get("outputActive"):
                    self.status = "OBS 已开始人工录制；本 PV 跳过自动录制"
                    self.restore_template()
                    return self.status
                self.client.request("StartRecord")
                self.owner = token
                self.owner_generation = self.client.stop_generation
                self.status = f"正在自动录制 PV{pvid:03d}；文件名：{filename}"
                self.log(self.status)
            except Exception:
                self.owner = None
                self.status = "录制启动失败或响应丢失；本 PV 不重试，请在 OBS 检查"
                self.restore_template()
            return self.status

    # 游戏崩溃、退出或心跳中断超过八秒时收尾自己拥有的录制。
    def watchdog(self):
        with self.lock:
            if self.last_heartbeat is not None and self.clock() - self.last_heartbeat > 8:
                self.stop_owned()
                self.restore_template()
                self.last_heartbeat = None

    # Helper 正常退出时尽力完成本功能录制收尾。
    def shutdown(self):
        with self.lock:
            self.stop_owned()
            self.restore_template()
            self.client.close()


# 使用 Windows 原生消息管道，拒绝远程客户端；一个快照对应一个短连接。
def serve_pipe(controller, stopping):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    kernel.CreateNamedPipeW.restype = wintypes.HANDLE
    kernel.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.WriteFile.argtypes = kernel.ReadFile.argtypes
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    kernel.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    invalid = ctypes.c_void_p(-1).value
    while not stopping.is_set():
        # FIRST_PIPE_INSTANCE 防止第二个 Helper 认领相同名称；默认 ACL 保持本机权限。
        pipe = kernel.CreateNamedPipeW(PIPE_NAME, 0x3 | 0x80000, 0x4 | 0x2 | 0x8, 1, 4096, 4096, 0, None)
        if pipe == invalid:
            print("无法创建本机管道；可能已有 Helper 正在运行", flush=True)
            stopping.set()
            return
        try:
            if not kernel.ConnectNamedPipe(pipe, None) and ctypes.get_last_error() != 535:
                continue
            buffer = ctypes.create_string_buffer(4096)
            count = wintypes.DWORD()
            if kernel.ReadFile(pipe, buffer, 4095, ctypes.byref(count), None):
                try:
                    parts = buffer.raw[:count.value].decode("ascii").strip().split()
                    if not ((len(parts) == 7 and parts[0] == "v1") or (len(parts) == 9 and parts[0] == "v2")):
                        raise ValueError()
                    pid, epoch, enabled, active, pvid, test = map(int, parts[1:7])
                    if pid <= 0 or epoch < 0 or enabled not in (0, 1) or active not in (0, 1):
                        raise ValueError()
                    title, non_vocal = "", False
                    if parts[0] == "v2":
                        if parts[7] not in ("0", "1"):
                            raise ValueError()
                        title = "" if parts[8] == "-" else bytes.fromhex(parts[8]).decode("utf-8")
                        non_vocal = parts[7] == "1"
                    reply = controller.process(pid, epoch, bool(enabled), bool(active), pvid, test, title, non_vocal)
                except Exception:
                    reply = "Helper 收到无效快照，已忽略"
                payload = reply[:500].encode("utf-8")
                kernel.WriteFile(pipe, payload, len(payload), ctypes.byref(count), None)
                # 等客户端读完再断开，避免未读状态消息被管道断开丢弃。
                kernel.FlushFileBuffers(pipe)
        finally:
            kernel.DisconnectNamedPipe(pipe)
            kernel.CloseHandle(pipe)


# 读取 Helper 独立 JSON 设置，仅支持本机 OBS，避免误连接其他机器。
def load_settings(path):
    if not path.exists():
        raise RuntimeError("缺少 Helper 配置，请复制 obs-helper.example.json 为 obs-helper.json 后填写密码")
    data = json.loads(path.read_text(encoding="utf-8"))
    host = data.get("host", "127.0.0.1")
    port = data.get("port", 4455)
    if host not in ("127.0.0.1", "localhost", "::1") or not isinstance(port, int) or not 1 <= port <= 65535:
        raise RuntimeError("Helper 配置只允许本机地址与有效端口")
    return host, port, str(data.get("password", ""))


# 运行后台管道服务；主线程保留可用的 Ctrl+C 与看门狗。
def main():
    # 统一中文控制台编码，避免 Windows 默认代码页乱码。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="DIVA PV 自动录制独立 OBS Helper", add_help=False)
    # 配置文件参数：保存本机 OBS 地址、端口与密码，不作为输出结果文件。
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("obs-helper.json"), help="Helper 私有 JSON 配置文件")
    parser.add_argument("--help", action="store_true", help="显示中文帮助")
    args = parser.parse_args()
    if args.help:
        print("独立 OBS Helper\n命令：python tools/obs_helper.py\n可选参数：--config 配置文件路径")
        return 0
    if os.name != "nt":
        print("OBS Helper 的本机管道只支持 Windows")
        return 1
    try:
        import websocket
        host, port, password = load_settings(args.config)
    except ImportError:
        print("缺少 WebSocket 依赖，请安装 tools/obs-requirements.txt 中的依赖")
        return 1
    except Exception as error:
        print("Helper 配置未就绪：" + (str(error) if isinstance(error, RuntimeError) else "请检查 JSON 文件格式"))
        return 1
    try:
        controller = RecordingController(ObsClient(host, port, password),
            recovery_path=args.config.with_name("obs-filename-recovery.json"),
            log_path=args.config.with_name("obs-recordings.log"))
    except RuntimeError as error:
        print(str(error))
        return 1
    stopping = threading.Event()
    thread = threading.Thread(target=serve_pipe, args=(controller, stopping), daemon=True)
    thread.start()
    print("OBS Helper 已启动；在游戏 PV 工具面板测试连接并启用自动录制。按 Ctrl+C 退出。", flush=True)
    try:
        while not stopping.wait(0.5):
            controller.watchdog()
    except KeyboardInterrupt:
        print("正在结束 Helper 并收尾本功能录制", flush=True)
    finally:
        stopping.set()
        controller.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
