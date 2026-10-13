#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计 Mod 歌曲表中注册的 Normal 歌曲是否已有原生歌词缓存。"""

import argparse
import json
import re
import sys
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


NORMAL_SCRIPT_PATTERN = re.compile(r"^pv_(\d+)\.difficulty\.normal\.0\.script_file_name=(.+)$")
LYRIC_PATTERN = re.compile(r"^pv_(\d+)\.lyric\.\d+=(.*)$")


def parse_arguments() -> argparse.Namespace:
    """解析歌曲表、缓存目录和报告输出路径。"""
    parser = argparse.ArgumentParser(description="审计 Mod 歌曲表注册项与原生歌词缓存覆盖。")
    parser.add_argument("--pv-db", type=Path, action="append", required=True, help="Mod 的 mod_pv_db.txt；可重复指定。")
    parser.add_argument("--cache-dir", type=Path, required=True, help="MMFreeLyrics 的正式 PVxxx.srt 缓存目录。")
    parser.add_argument("--report", type=Path, required=True, help="输出 UTF-8 JSON 审计报告文件。")
    return parser.parse_args()


def load_registered_songs(database_paths: list[Path]) -> tuple[dict[int, str], set[int]]:
    """读取 Normal 脚本注册项和含有歌词文本的逻辑歌曲编号。"""
    normal_scripts: dict[int, str] = {}
    lyric_ids: set[int] = set()
    for database_path in database_paths:
        for raw_line in database_path.read_text(encoding="utf-8").splitlines():
            script_match = NORMAL_SCRIPT_PATTERN.match(raw_line)
            if script_match is not None:
                pv_id = int(script_match.group(1))
                script_name = script_match.group(2)
                existing = normal_scripts.get(pv_id)
                if existing is not None and existing != script_name:
                    raise ValueError(f"PV{pv_id:03d} 在多个文本表声明了不同 Normal 脚本。")
                normal_scripts[pv_id] = script_name
            lyric_match = LYRIC_PATTERN.match(raw_line)
            if lyric_match is not None:
                lyric_ids.add(int(lyric_match.group(1)))
    if not normal_scripts:
        raise ValueError("文本表中未找到任何 Normal 脚本注册项。")
    return normal_scripts, lyric_ids


def main() -> int:
    """逐首核对注册歌曲的正式缓存，并区分无歌词文本的有效歌曲。"""
    arguments = parse_arguments()
    try:
        if not arguments.cache_dir.is_dir() or not all(path.is_file() for path in arguments.pv_db):
            raise ValueError("歌词缓存目录或歌曲文本表不存在。")
        normal_scripts, lyric_ids = load_registered_songs(arguments.pv_db)
        report = {"schema_version": 1, "pv_db": [str(path) for path in arguments.pv_db], "cache_dir": str(arguments.cache_dir), "covered": [], "no_lyric_text": [], "failed": []}
        for pv_id, script_name in sorted(normal_scripts.items()):
            cache_path = arguments.cache_dir / f"PV{pv_id}.srt"
            if pv_id not in lyric_ids:
                report["no_lyric_text"].append({"pv_id": pv_id, "script_file_name": script_name, "reason": "歌曲表没有 lyric 文本键，不应伪造空缓存。"})
            elif cache_path.is_file():
                report["covered"].append({"pv_id": pv_id, "script_file_name": script_name, "cache": str(cache_path)})
            else:
                report["failed"].append({"pv_id": pv_id, "script_file_name": script_name, "error": "歌曲表包含 lyric 文本，但正式 SRT 缓存不存在。"})
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"歌曲表审计完成：覆盖 {len(report['covered'])}，无歌词文本 {len(report['no_lyric_text'])}，失败 {len(report['failed'])}。报告：{arguments.report}")
        return 0 if not report["failed"] else 1
    except (OSError, ValueError) as error:
        print(f"歌曲表审计失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
