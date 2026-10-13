#!/usr/bin/env python3
"""审计官方日文歌词与罗马音能否作为振假名离线原型的输入。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


KANJI_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ENTRY_PATTERN = re.compile(r"^pv_(?P<pv_id>\d+)\.(?P<kind>lyric(?:_en)?)\.(?P<index>\d+)=(?P<text>.*)$")


def read_lyric_pairs(database_path: Path, pv_id: int) -> dict[int, dict[str, str]]:
    """读取指定 PV 的日文歌词和同编号罗马音，按歌词编号配对。"""
    pairs: dict[int, dict[str, str]] = {}
    with database_path.open("r", encoding="utf-8-sig") as source:
        for raw_line in source:
            match = ENTRY_PATTERN.match(raw_line.rstrip("\r\n"))
            if not match or int(match.group("pv_id")) != pv_id:
                continue
            index = int(match.group("index"))
            kind = match.group("kind")
            pairs.setdefault(index, {})[kind] = match.group("text")
    return pairs


def build_report(database_path: Path, pv_id: int) -> dict[str, object]:
    """生成可复核的输入覆盖率报告，不把罗马音误称为逐字读音标注。"""
    pairs = read_lyric_pairs(database_path, pv_id)
    rows: list[dict[str, object]] = []
    paired_count = 0
    kanji_count = 0
    missing_japanese: list[int] = []
    missing_romaji: list[int] = []
    for index in sorted(pairs):
        japanese = pairs[index].get("lyric", "")
        romaji = pairs[index].get("lyric_en", "")
        has_kanji = bool(KANJI_PATTERN.search(japanese))
        if japanese and romaji:
            paired_count += 1
        if has_kanji:
            kanji_count += 1
        if not japanese:
            missing_japanese.append(index)
        if not romaji:
            missing_romaji.append(index)
        rows.append(
            {
                "index": index,
                "japanese": japanese,
                "romaji": romaji,
                "containsKanji": has_kanji,
                "hasPair": bool(japanese and romaji),
            }
        )
    return {
        "pvId": pv_id,
        "source": str(database_path),
        "totalEntries": len(rows),
        "pairedEntries": paired_count,
        "entriesWithKanji": kanji_count,
        "missingJapanese": missing_japanese,
        "missingRomaji": missing_romaji,
        "conclusion": (
            "逐行日文与罗马音输入完整，可作为形态分析结果的交叉校验；"
            "罗马音未标注词或汉字边界，不能单独作为可靠的逐字振假名来源。"
        ),
        "rows": rows,
    }


def parse_arguments() -> argparse.Namespace:
    """解析离线审计所需的官方文本表、PV 编号和输出文件路径。"""
    parser = argparse.ArgumentParser(description="审计日文歌词与罗马音的振假名输入覆盖率")
    parser.add_argument("--pv-db", type=Path, required=True, help="官方 mdata_pv_db.txt 文件路径")
    parser.add_argument("--pv-id", type=int, required=True, help="要审计的 PV 编号")
    parser.add_argument("--out-json", type=Path, required=True, help="审计报告 JSON 输出路径")
    return parser.parse_args()


def main() -> int:
    """执行离线审计并输出中文结论，供后续独立振假名原型消费。"""
    sys.stdout.reconfigure(encoding="utf-8")
    arguments = parse_arguments()
    report = build_report(arguments.pv_db, arguments.pv_id)
    arguments.out_json.parent.mkdir(parents=True, exist_ok=True)
    arguments.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已审计 PV{arguments.pv_id}：共 {report['totalEntries']} 行，完整日文/罗马音配对 {report['pairedEntries']} 行。")
    print(f"其中含汉字的行数：{report['entriesWithKanji']}；报告已写入：{arguments.out_json}")
    print("结论：可做离线振假名原型，但必须以日文形态分析器提供词级读音，罗马音仅用于校验。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
