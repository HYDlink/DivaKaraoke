#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在新电脑按发布锁定清单准备开放字体，不下载游戏或私人数据。"""
from pathlib import Path
import hashlib
import json
import sys
import urllib.request

from export_lyrics import ChineseArgumentParser

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """校验现有开放字体或下载固定版本，输出目录不保存认证数据。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="准备公开打包所需的固定版本OFL字体。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助。")
    # 输出结果目录参数：保存锁定的开放字体，不读取用户字体或游戏资料。
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets", help="开放字体下载输出目录。")
    args = parser.parse_args()
    lock = json.loads((ROOT / "release-dependencies.json").read_text(encoding="utf-8"))
    for item in lock["文件"]:
        if not item["文件"].startswith("assets/fonts/"):
            continue
        relative = Path(item["文件"]).relative_to("assets")
        target = args.output_dir / relative
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == item["SHA256"]:
            print("开放字体已存在且哈希一致。")
            continue
        url = item["来源"]
        if not url.startswith("https://raw.githubusercontent.com/google/fonts/"):
            raise ValueError("下载地址不属于锁定的Google Fonts官方来源。")
        print("正在下载固定版本开放日文字体。")
        request = urllib.request.Request(url, headers={"User-Agent": "DivaKaraoke-release"})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item["SHA256"] or len(data) != item["字节"]:
            raise ValueError("字体下载内容不符合发布锁定清单。")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print("开放字体下载与SHA-256校验通过。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print("开放资产准备失败：" + str(error), file=sys.stderr)
        raise SystemExit(1)
