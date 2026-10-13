#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验单首 PV 的原生歌词 JSON 与派生 SRT 缓存是否一致。"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main() -> int:
    """校验单曲 JSON 与 SRT 的时间和文本是否完全一致。"""
    parser = argparse.ArgumentParser(description="校验一首已生成的原生歌词 JSON 与派生 SRT 缓存。")
    parser.add_argument("--timeline-json", type=Path, required=True, help="待校验的原生歌词 JSON 缓存文件。")
    parser.add_argument("--srt", type=Path, required=True, help="待校验的同源 UTF-8 SRT 缓存文件。")
    arguments = parser.parse_args()
    try:
        document = json.loads(arguments.timeline_json.read_text(encoding="utf-8"))
        lines = [(item["start_ms"], item["end_ms"], item["text"]) for item in document["lines"]]
        # 不使用 strip()：官方末句可以包含有意义的尾随空格，删掉会使 JSON/SRT 校验失真。
        source = arguments.srt.read_text(encoding="utf-8")
        block_starts = list(re.finditer(
            r"(?m)^(\d+)\r?\n(\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d)\r?\n",
            source,
        ))
        if not block_starts:
            raise ValueError("SRT 中未找到任何编号时间块。")
        srt_lines = []
        for index, block_start in enumerate(block_starts, 1):
            number, timestamp = block_start.group(1), block_start.group(2)
            content_end = block_starts[index].start() if index < len(block_starts) else len(source)
            content = source[block_start.end():content_end]
            # 每个块之间由两个换行符分隔；仅移除分隔符，保留文本本身的一切空白。
            text = re.sub(r"\r?\n\r?\n$", "", content)
            # 最后一个块只有文件末尾换行；它不是歌词正文的一部分。
            text = re.sub(r"\r?\n$", "", text)
            match = re.fullmatch(r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)", timestamp)
            if number != str(index) or match is None:
                raise ValueError(f"SRT 第 {index} 块格式无效。")
            values = [int(value) for value in match.groups()]
            start = values[0] * 3600000 + values[1] * 60000 + values[2] * 1000 + values[3]
            end = values[4] * 3600000 + values[5] * 60000 + values[6] * 1000 + values[7]
            srt_lines.append((start, end, text))
        if document.get("schema_version") != 1 or not lines or lines != srt_lines:
            raise ValueError("JSON 与 SRT 的架构、行数、时间或文本不一致。")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"校验失败：{error}", file=sys.stderr)
        return 1
    print(f"校验成功：PV{document['pv_id']:03d}，JSON 与 SRT 共 {len(lines)} 行，时间与文本完全一致。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
