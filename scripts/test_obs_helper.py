#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBS 状态机模拟测试：不连接 OBS，不开始真实录像。"""
import importlib.util
from pathlib import Path
import sys
import tempfile
import os

spec = importlib.util.spec_from_file_location("obs_helper", Path(__file__).resolve().parents[1] / "tools" / "obs_helper.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class FakeObs:
    # 初始化模拟 OBS，记录请求并支持响应丢失。
    def __init__(self, active=False):
        self.socket = object()
        self.stop_generation = 0
        self.active = active
        self.calls = []
        self.lose_start_response = False
        self.directory = tempfile.TemporaryDirectory()
        self.template = "%CCYY-%MM-%DD"
        self.profile = "测试配置"
        self.outputs = []
        self.fail_set = False
        self.stopping_polls = 0
        self.remaining_polls = 0

    # 模拟实际录制状态；启动成功但响应丢失会断开连接。
    def request(self, kind, request_data=None):
        self.calls.append(kind)
        if self.socket is None:
            self.socket = object()
        if kind == "GetRecordStatus":
            if self.remaining_polls:
                self.remaining_polls -= 1
                return {"outputActive": True}
            return {"outputActive": self.active}
        if kind == "GetRecordDirectory":
            return {"recordDirectory": self.directory.name}
        if kind == "GetProfileList":
            return {"currentProfileName": self.profile}
        if kind == "GetProfileParameter":
            return {"parameterValue": self.template}
        if kind == "SetProfileParameter":
            assert request_data["parameterCategory"] == "Output"
            assert request_data["parameterName"] == "FilenameFormatting"
            if self.fail_set:
                raise RuntimeError("模拟命名失败")
            self.template = request_data["parameterValue"]
        if kind == "StartRecord":
            self.output = str(Path(self.directory.name) / (self.template + ".mkv"))
            self.active = True
            if self.lose_start_response:
                self.socket = None
                raise RuntimeError("模拟启动响应丢失")
        elif kind == "StopRecord":
            self.active = False
            self.remaining_polls = self.stopping_polls
            self.stop_generation += 1
            Path(self.output).write_bytes(b"test")
            self.outputs.append(self.output)
            return {"outputPath": self.output}
        return {}

    # 模拟断线，重连后必须放弃旧所有权。
    def close(self):
        self.socket = None


# 发送统一快照，不访问真实游戏内存。
def snapshot(controller, epoch=1, enabled=True, active=True, pvid=424):
    return controller.process(999, epoch, enabled, active, pvid, 0)


# 验证开始去重、暂停保持、退出、一首一个文件与关闭收尾。
def test_lifecycle():
    obs = FakeObs()
    controller = helper.RecordingController(obs)
    snapshot(controller, active=False)
    assert "StartRecord" not in obs.calls
    snapshot(controller)
    for _ in range(5):
        snapshot(controller)  # DLL 暂停时保持 active 为真。
    assert obs.calls.count("StartRecord") == 1
    assert "StopRecord" not in obs.calls
    snapshot(controller, active=False)
    assert obs.calls.count("StopRecord") == 1
    snapshot(controller, epoch=2)
    assert obs.calls.count("StartRecord") == 2
    snapshot(controller, epoch=2, enabled=False)
    assert obs.calls.count("StopRecord") == 2


# 验证人工录制不认领，人工停止再启动后不停止新的录像。
def test_manual_ownership():
    obs = FakeObs(active=True)
    controller = helper.RecordingController(obs)
    snapshot(controller)
    snapshot(controller, active=False)
    assert obs.calls == ["GetRecordStatus"]
    obs = FakeObs()
    controller = helper.RecordingController(obs)
    snapshot(controller)
    obs.stop_generation += 2
    obs.active = True
    snapshot(controller, active=False)
    assert "StopRecord" not in obs.calls
    assert controller.owner is None


# 验证启动响应丢失不重试、不停止无法确认所属的录像。
def test_lost_response():
    obs = FakeObs()
    obs.lose_start_response = True
    controller = helper.RecordingController(obs)
    snapshot(controller)
    snapshot(controller)
    snapshot(controller, active=False)
    assert obs.active
    assert obs.calls.count("StartRecord") == 1
    assert "StopRecord" not in obs.calls
    assert controller.owner is None


# 验证断线重连释放所有权。
def test_reconnect():
    obs = FakeObs()
    controller = helper.RecordingController(obs)
    snapshot(controller)
    obs.close()
    snapshot(controller, active=False)
    assert "StopRecord" not in obs.calls
    assert controller.owner is None


# 验证游戏异常退出与 Helper 正常退出仅收尾本功能录像。
def test_watchdog():
    clock = [0.0]
    obs = FakeObs()
    controller = helper.RecordingController(obs, clock=lambda: clock[0])
    snapshot(controller)
    clock[0] = 7.9
    controller.watchdog()
    assert "StopRecord" not in obs.calls
    clock[0] = 8.1
    controller.watchdog()
    assert obs.calls.count("StopRecord") == 1
    snapshot(controller, epoch=2)
    controller.shutdown()
    assert obs.calls.count("StopRecord") == 2


# 验证官方认证规则与录制停止事件解析，不打印密码。
def test_protocol():
    import base64
    import hashlib
    secret = base64.b64encode(hashlib.sha256(b"passwordsalt").digest())
    expected = base64.b64encode(hashlib.sha256(secret + b"challenge").digest()).decode()
    assert helper.ObsClient.authentication("password", "salt", "challenge") == expected
    obs = helper.ObsClient()
    obs.handle_event({"op": 5, "d": {"eventType": "RecordStateChanged", "eventData": {
        "outputState": "OBS_WEBSOCKET_OUTPUT_STOPPED"}}})
    assert obs.stop_generation == 1


# 两首不用重新开启，标题、后缀、先命名后启动、独立路径及模板恢复都必须正确。
def test_playlist_naming():
    obs = FakeObs()
    original = obs.template
    controller = helper.RecordingController(obs)
    controller.process(999, 1, True, True, 424, 0, "恋愛裁判", False)
    assert obs.template == "恋愛裁判-On Vocal"
    assert obs.calls.index("SetProfileParameter") < obs.calls.index("StartRecord")
    controller.process(999, 2, True, True, 824, 0, "愛Dee", True)
    assert len(obs.outputs) == 1
    assert Path(obs.outputs[0]).name == "恋愛裁判-On Vocal.mkv"
    controller.process(999, 2, True, False, 824, 0, "愛Dee", True)
    assert Path(obs.outputs[1]).name == "愛Dee-Off Vocal.mkv"
    assert len(set(controller.saved_outputs)) == 2
    assert obs.template == original
    controller.process(999, 3, True, True, 824, 0, "愛Dee", True)
    assert obs.template == "愛Dee-Off Vocal (2)"
    controller.shutdown()


# 验证非法字符、模板转义、无标题、Unicode 长度和保留名。
def test_filename_safety():
    assert helper.safe_recording_stem('A/B:%CCYY*?', 424, False) == "A_B_％CCYY__-On Vocal"
    assert helper.safe_recording_stem(" . ", 424, True) == "PV424-Off Vocal"
    assert helper.safe_recording_stem("CON", 1, False).startswith("_CON")
    assert len(helper.safe_recording_stem("歌" * 200, 1, False)) < 130
    obs = FakeObs()
    Path(obs.directory.name, "TEST-On Vocal.mp4").write_bytes(b"test")
    controller = helper.RecordingController(obs)
    controller.process(999, 1, True, True, 424, 0, "test", False)
    assert obs.template == "test-On Vocal (2)"
    controller.shutdown()


# 模板设置失败不能以默认文件名继续录制，模板恢复不得覆盖用户改动。
def test_template_failure_and_edits():
    obs = FakeObs()
    obs.fail_set = True
    controller = helper.RecordingController(obs)
    snapshot(controller)
    assert "StartRecord" not in obs.calls
    obs.fail_set = False
    snapshot(controller, epoch=2)
    obs.template = "用户新模板"
    snapshot(controller, epoch=2, active=False)
    assert obs.template == "用户新模板"


# 持久化恢复跨 Helper 重启生效，配置切换时等待原配置，不接管未知录像。
def test_template_recovery():
    obs = FakeObs()
    original = obs.template
    recovery = Path(obs.directory.name, "恢复.json")
    controller = helper.RecordingController(obs, recovery_path=recovery)
    snapshot(controller)
    assert recovery.exists()
    restarted = helper.RecordingController(obs, recovery_path=recovery)
    obs.profile = "另一配置"
    assert not restarted.restore_template()
    obs.profile = "测试配置"
    assert restarted.restore_template()
    assert obs.template == original
    assert not recovery.exists()
    assert "StopRecord" not in obs.calls
    controller.shutdown()


# 模拟 StopRecord 已返回但封装仍活动，下一首必须等停止完成再启动。
def test_delayed_stop():
    obs = FakeObs()
    obs.stopping_polls = 2
    controller = helper.RecordingController(obs)
    snapshot(controller)
    snapshot(controller, epoch=2, pvid=824)
    assert obs.calls.count("StartRecord") == 2
    assert len(obs.outputs) == 1
    assert obs.remaining_polls == 0
    controller.shutdown()


# 同一活跃会话重连时仅恢复遗留模板，绝不重复启动或停止未知录制。
def test_recovery_while_active():
    obs = FakeObs()
    controller = helper.RecordingController(obs)
    original = obs.template
    snapshot(controller)
    controller.owner = None
    obs.fail_set = True
    snapshot(controller)
    assert controller.template_backup is not None
    obs.fail_set = False
    snapshot(controller)
    assert controller.template_backup is None and obs.template == original
    assert obs.calls.count("StartRecord") == 1 and "StopRecord" not in obs.calls


# 验证真实 Windows Named Pipe 收发，但录制请求只交给模拟 OBS。
def test_named_pipe():
    import ctypes
    from ctypes import wintypes
    import threading
    import time
    # 使用测试专属管道，避免与用户已经运行的正式 Helper 争用。
    helper.PIPE_NAME = rf"\\.\pipe\DivaKaraokeObsRegression{os.getpid()}"
    obs = FakeObs()
    controller = helper.RecordingController(obs)
    stop = threading.Event()
    server = threading.Thread(target=helper.serve_pipe, args=(controller, stop), daemon=True)
    server.start()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.WriteFile.argtypes = kernel.ReadFile.argtypes
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    title = "管道日文検証"
    messages = [f"v2 999 1 1 1 424 0 1 {title.encode('utf-8').hex()}\n".encode("ascii"),
                b"v1 999 1 1 0 424 0\n"]
    for message in messages:
        deadline = time.monotonic() + 3
        pipe = ctypes.c_void_p(-1).value
        while time.monotonic() < deadline:
            pipe = kernel.CreateFileW(helper.PIPE_NAME, 0xC0000000, 0, None, 3, 0, None)
            if pipe != ctypes.c_void_p(-1).value:
                break
            time.sleep(0.01)
        assert pipe != ctypes.c_void_p(-1).value
        try:
            count = wintypes.DWORD()
            assert kernel.WriteFile(pipe, message, len(message), ctypes.byref(count), None)
            buffer = ctypes.create_string_buffer(2048)
            assert kernel.ReadFile(pipe, buffer, 2047, ctypes.byref(count), None)
            assert "录制" in buffer.raw[:count.value].decode("utf-8")
        finally:
            kernel.CloseHandle(pipe)
    stop.set()
    assert obs.calls.count("StartRecord") == 1
    assert obs.calls.count("StopRecord") == 1
    assert Path(obs.outputs[0]).name == "管道日文検証-Off Vocal.mkv"


# 以中文汇总测试，不使用默认英文测试输出。
def main():
    # Windows 控制台也显式使用 UTF-8 中文输出。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    tests = [test_lifecycle, test_manual_ownership, test_lost_response,
             test_reconnect, test_watchdog, test_protocol, test_playlist_naming,
             test_filename_safety, test_template_failure_and_edits, test_template_recovery,
             test_delayed_stop, test_recovery_while_active, test_named_pipe]
    for index, test in enumerate(tests, 1):
        try:
            test()
        except Exception:
            print(f"OBS 模拟测试第 {index} 项失败")
            return 1
    print(f"OBS 模拟测试通过：{len(tests)} 项；未连接 OBS、未进行真实录制")
    return 0


if __name__ == "__main__":
    sys.exit(main())
