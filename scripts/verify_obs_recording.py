#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用合成的两首会话验证真实 OBS 命名和停止输出，不代表游戏播放列表验收。"""
import argparse
import importlib.util
from pathlib import Path
import sys
import time


# 真实短录制仅在显式指定时执行，默认只检查连接与接口。
def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="OBS 连接器验证", add_help=False)
    # 配置路径仅用于读取本机连接密码，不写入报告或日志。
    parser.add_argument("--config", required=True, type=Path)
    # 显式启用两段各两秒的真实短录制，结果使用 OBS 当前输出目录。
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("obs_helper", Path(__file__).resolve().parents[1] / "tools/obs_helper.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    client = helper.ObsClient(*helper.load_settings(args.config))
    controller = helper.RecordingController(client)
    try:
        version = client.request("GetVersion")
        print(f'OBS 版本：{version["obsVersion"]}；WebSocket：{version["obsWebSocketVersion"]}')
        required = {"GetProfileList", "GetProfileParameter", "SetProfileParameter", "GetRecordDirectory", "StartRecord", "StopRecord"}
        if not required.issubset(version["availableRequests"]):
            raise RuntimeError("OBS 缺少必要接口")
        if client.request("GetRecordStatus")["outputActive"]:
            raise RuntimeError("OBS 当前正在录制；验证未操作已有录制")
        original = client.request("GetProfileParameter", {"parameterCategory": "Output", "parameterName": "FilenameFormatting"}).get("parameterValue")
        print("认证与命名接口检查通过；当前 OBS 空闲")
        if not args.record:
            return 0
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for epoch, title, non_vocal in ((1, f"OBS连接器验证-{stamp}-恋愛裁判", False),
                                      (2, f"OBS连接器验证-{stamp}-愛Dee", True)):
            print(controller.process(999999, epoch, True, True, 424 if epoch == 1 else 824, 0, title, non_vocal))
            if controller.owner is None:
                raise RuntimeError("真实短录制未成功启动")
            time.sleep(2)
        print(controller.process(999999, 2, True, False, 824, 0))
        for saved in controller.saved_outputs:
            path = Path(saved)
            deadline = time.monotonic() + 4
            while (not path.exists() or path.stat().st_size == 0) and time.monotonic() < deadline:
                time.sleep(0.1)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError("OBS 返回的录像文件不存在或为空")
            print(f"已确认文件：{path}；大小：{path.stat().st_size} 字节")
        restored = client.request("GetProfileParameter", {"parameterCategory": "Output", "parameterName": "FilenameFormatting"}).get("parameterValue")
        if len(set(controller.saved_outputs)) != 2 or restored != original:
            raise RuntimeError("两首独立文件或模板恢复检查失败")
        if "-On Vocal" not in controller.saved_outputs[0] or "-Off Vocal" not in controller.saved_outputs[1]:
            raise RuntimeError("真实文件名后缀不符合预期")
        print("真实 OBS 两段录制通过：独立路径、日文命名、人声后缀和原模板恢复；游戏播放列表仍待验收")
        return 0
    except Exception as error:
        print("OBS 验证未通过：" + (str(error) if isinstance(error, RuntimeError) else "请检查连接或录像文件"))
        return 1
    finally:
        controller.shutdown()


if __name__ == "__main__":
    sys.exit(main())
