#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用设备私有配置启动日常歌词工具，不猜测维护者或玩家的目录。"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from export_lyrics import ChineseArgumentParser
from local_environment import ROOT, configuration_path, load_environment


def build_command(action: str, config: Path, values: dict[str, Path]) -> list[str]:
    """生成有限操作的命令；只有明确选择安装或应用时才加入安装目标。"""
    output = values.get("output_dir", ROOT / "artifacts/exported-lyrics")
    manual = values.get("manual_singers_dir", output / "manual-singers")
    if action == "singers":
        return [sys.executable, str(ROOT / "scripts/build_singer_timeline.py"),
                "--cache-dir", str(output / "cache"), "--output-dir", str(output / "singer-preview"),
                "--manual-dir", str(manual)]
    command = [sys.executable, str(ROOT / "scripts/export_lyrics.py"), "--local-config", str(config)]
    if action in {"install", "apply"}:
        target = values.get("install_dir")
        if target is None and (ROOT / "DivaKaraoke.dll").is_file():
            target = ROOT / "lyrics"
        if target is None:
            raise ValueError("请先在本地配置中填写install_dir；工具不会猜测游戏的安装位置。")
        command.extend(["--install-dir", str(target), "--install-only" if action == "install" else "--rebuild-singers-only"])
    return command


def main() -> int:
    """解析明确操作与本地配置，可只读预览即将执行的命令。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="读取.local/environment.toml启动日常工具。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助。")
    # 操作参数：导出、生成歌手预览、应用人工歌手标记或安装现有缓存。
    parser.add_argument("action", choices=("export", "singers", "apply", "install"), help="明确选择要执行的操作。")
    # 本地配置参数：所有设备路径只从此私有文件或工具自己的命令行参数取得。
    parser.add_argument("--local-config", type=Path, help="私有路径配置文件，默认.local/environment.toml。")
    # 只读预览参数：输出操作与命令，不生成结果、不写入游戏。
    parser.add_argument("--dry-run", action="store_true", help="只预览命令，不执行。")
    args = parser.parse_args()
    config = configuration_path(args.local_config)
    values = load_environment(config, required=True)
    command = build_command(args.action, config, values)
    if args.dry_run:
        print(json.dumps({"操作": args.action, "命令": command, "已执行": False}, ensure_ascii=False, indent=2))
        return 0
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print("工具未启动：" + str(error), file=sys.stderr)
        raise SystemExit(2)
