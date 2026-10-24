#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读研究《Dear》口型与已知歌词元音的关系，不生成正式逐字时间或修改游戏。"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import build_singer_timeline as singer
import furigana_alignment as reading

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_DB = ROOT / "artifacts/main-region-extract/rom_steam_region/rom/pv_db.txt"
# 这是从本曲前四句归纳的候选对应，不是跨版本口型编号标准；O/U在本曲无法区分。
POSE_CLASSES = {24: "A", 25: "OU", 31: "I", 32: "E"}
CLASS_KEYS = {24: "a", 25: "o", 31: "i", 32: "e"}


def parse_arguments() -> argparse.Namespace:
    """读取单曲缓存、研究输出位置与同曲难度检查参数。"""
    parser = argparse.ArgumentParser(description="核对PV045官方口型与歌词元音，仅保存研究证据。")
    # 缓存输入参数：用于追溯已有DSC，正文仍与官方数据库独立核对。
    parser.add_argument("--cache", type=Path, default=ROOT / "artifacts/singer-full-export/cache/PV045.json", help="已有PV045歌词缓存。")
    # 输出结果目录参数：保存证据JSON、中文逐句表与首句候选锚点，不写运行时缓存。
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/pv045-mouth-research", help="UTF-8研究结果输出目录。")
    # 同曲检查参数：仅比较PV045已提取的其他难度，不扫描曲库或重新解包。
    parser.add_argument("--verify-difficulties", action="store_true", help="核对同曲另外三个难度的完整口型序列。")
    return parser.parse_args()


def alignment_evidence(expected: str, actual: str) -> dict:
    """保留最小编辑距离下所有可能匹配位置，不用单条贪心路径伪造确定切点。"""
    n, m = len(expected), len(actual)
    forward = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        forward[i][0] = i
    for j in range(m + 1):
        forward[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            forward[i][j] = min(forward[i - 1][j] + 1, forward[i][j - 1] + 1,
                                forward[i - 1][j - 1] + (expected[i - 1] != actual[j - 1]))
    backward = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n, -1, -1):
        backward[i][m] = n - i
    for j in range(m, -1, -1):
        backward[n][j] = m - j
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            backward[i][j] = min(backward[i + 1][j] + 1, backward[i][j + 1] + 1,
                                 backward[i + 1][j + 1] + (expected[i] != actual[j]))
    cost = forward[n][m]
    possibilities = []
    for i, vowel in enumerate(expected):
        matches = [j for j in range(m) if vowel == actual[j]
                   and forward[i][j] + backward[i + 1][j + 1] == cost]
        deleted = any(forward[i][j] + 1 + backward[i + 1][j] == cost for j in range(m + 1))
        substituted = any(vowel != actual[j] and forward[i][j] + 1 + backward[i + 1][j + 1] == cost
                          for j in range(m))
        possibilities.append({"vowel_index": i, "matching_event_positions": matches,
                              "may_be_deleted": deleted, "may_be_substituted": substituted,
                              "unique_under_this_model": len(matches) == 1 and not deleted and not substituted})
    return {"edit_distance": cost, "vowel_candidates": possibilities}


def first_line_anchors(row: dict, audit_row: dict) -> list[dict]:
    """只为首句完全一致的序列输出读音与正文候选锚点，真实发声终点保持未知。"""
    if not row["exact_class_sequence"] or audit_row["alignment"]["status"] != "aligned":
        raise ValueError("首句元音或既有正文读音映射不完整，拒绝输出候选。")
    alignment = audit_row["alignment"]
    source = alignment["source_normalized"]
    units, cursor = [], 0
    while cursor < len(source):
        token = next((source[cursor:cursor + size] for size in (3, 2, 1)
                      if source[cursor:cursor + size] in reading.ROMAN), None)
        if token is None:
            raise ValueError("首句包含当前示例不支持的非元音单元，拒绝猜测。")
        units.append({"romaji": token, "kana": reading.ROMAN[token], "start": cursor, "end": cursor + len(token)})
        cursor += len(token)
    if len(units) != len(row["vowel_events"]):
        raise ValueError("首句音节数与元音口型数不一致。")
    result = []
    for number, (unit, event) in enumerate(zip(units, row["vowel_events"]), 1):
        if unit["romaji"][-1].replace("u", "o") != CLASS_KEYS[event["params"][2]]:
            raise ValueError("首句审计音节与口型候选类别不符。")
        segments = [segment for segment in alignment["segments"] if len(segment["candidates"]) == 1
                    and segment["candidates"][0]["source_start"] <= unit["start"]
                    and segment["candidates"][0]["source_end"] >= unit["end"]]
        if len(segments) != 1:
            raise ValueError("首句正文单元映射不唯一。")
        segment = segments[0]
        start, length = segment["start"], segment["length"]
        if segment["kind"] == "kana":
            source_start = segment["candidates"][0]["source_start"]
            prefix = reading.strict_romaji(source[source_start:unit["start"]])
            if prefix is None:
                raise ValueError("首句固定假名的前缀无法完整转换。")
            start, length = start + len(prefix), len(unit["kana"])
        result.append({"number": number, "kana": unit["kana"], "romaji": unit["romaji"],
                       "text_start": start, "text_length": length, "text": row["text"][start:start + length],
                       "command_ms": event["raw_time"] / 100, "command_index": event["index"],
                       "command_offset": event["offset"], "pose": event["params"][2],
                       "transition_raw": event["params"][3], "vocal_start_ms": None, "vocal_end_ms": None,
                       "next_vowel_command_ms": row["vowel_events"][number]["raw_time"] / 100
                       if number < len(units) else None})
    return result


def build_report(cache_path: Path, verify_difficulties: bool) -> dict:
    """重读官方单曲资料，核对缓存、分支、难度及元音序列并保存未解决的边界。"""
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if cache["pv_id"] != 45:
        raise ValueError("本研究仅支持PV045。")
    dsc = Path(cache["source"]["dsc"])
    if dsc.resolve() != Path("F:/DivaKaraOkeLyrics/main-extract/rom/script/pv_045_normal.dsc").resolve():
        raise ValueError("本研究要求已有官方基础包PV045普通难度，不混用Mod脚本。")
    opcode = Path(cache["source"]["opcode_db"])
    fields = dict(re.findall(r"^pv_045\.(.+?)=(.*)$", OFFICIAL_DB.read_text(encoding="utf-8"), re.M))
    if fields["song_name"] != "Dear":
        raise ValueError("官方数据库曲名不符。")
    commands, events, pv_end = singer.read_commands(dsc, opcode)
    if [(x["raw_time"], x["params"][0]) for x in commands if x["name"] == "LYRIC"] != events:
        raise ValueError("观察器歌词事件与生产读取器返回不符。")
    lyrics = singer.extractor.load_lyrics([OFFICIAL_DB], 45, True)
    rebuilt = singer.extractor.build_lines(events, lyrics, pv_end)
    keys = ("start_ms", "end_ms", "text", "lyric_id", "raw_time")
    if [tuple(x[k] for k in keys) for x in rebuilt] != [tuple(x[k] for k in keys) for x in cache["lines"]]:
        raise ValueError("官方重建时间线与已有缓存不同，停止关联。")
    mouths = [x for x in commands if x["name"] == "MOUTH_ANIM"]
    if any(x["branch"] != 0 or x["params"][0] != 0 for x in mouths):
        raise ValueError("本研究只接受全局分支的单角色口型。")
    if any(x["name"] in {"EDIT_MOUTH", "EDIT_MOUTH_ANIM"} for x in commands):
        raise ValueError("出现隐式口型，不能只用MOUTH_ANIM。")
    if any(a["raw_time"] > b["raw_time"] for a, b in zip(mouths, mouths[1:])):
        raise ValueError("口型时间回退，不能使用线性窗口。")
    if set(x["params"][2] for x in mouths) - set(POSE_CLASSES) - {28}:
        raise ValueError("出现本曲候选表未覆盖的姿态，不自动扩展映射。")
    rows = []
    for index, line in enumerate(rebuilt):
        if not line["text"].strip():
            continue
        end_raw = rebuilt[index + 1]["raw_time"] if index + 1 < len(rebuilt) else pv_end
        selected = [x for x in mouths if line["raw_time"] <= x["raw_time"] < end_raw]
        vowel_events = [x for x in selected if x["params"][2] in POSE_CLASSES]
        romaji = fields[f"lyric_en.{line['lyric_id']:03d}"].strip()
        expected = "".join(re.findall("[aiueo]", romaji.lower()))
        expected_classes = expected.replace("u", "o")
        actual = "".join(CLASS_KEYS[x["params"][2]] for x in vowel_events)
        rows.append({"runtime_line": len(rows) + 1, **line, "romaji": romaji,
                     "expected_vowels": expected, "expected_classes": expected_classes,
                     "actual_classes": actual, "exact_class_sequence": expected_classes == actual,
                     "alignment": alignment_evidence(expected_classes, actual),
                     "first_vowel_minus_lyric_ms": (vowel_events[0]["raw_time"] - line["raw_time"]) / 100
                     if vowel_events else None, "vowel_events": vowel_events, "mouth_events": selected})
    comparisons = []
    if verify_difficulties:
        reference = [(x["raw_time"], x["params"], x["branch"]) for x in mouths]
        for name in ("easy", "hard", "extreme"):
            path = dsc.with_name(f"pv_045_{name}.dsc")
            other, _, _ = singer.read_commands(path, opcode)
            sequence = [(x["raw_time"], x["params"], x["branch"]) for x in other if x["name"] == "MOUTH_ANIM"]
            comparisons.append({"difficulty": name, "input": singer.digest(path), "mouth_count": len(sequence),
                                "exact_match": sequence == reference})
    audit_path = cache_path.with_suffix(".ruby.audit.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_row = audit["rows"][0]
    if audit_row["japanese"] != rows[0]["text"] or audit_row["romaji"] != rows[0]["romaji"]:
        raise ValueError("首句注音审计与官方正文/唱法不符。")
    anchors = first_line_anchors(rows[0], audit_row)
    return {"pv_id": 45, "song": "Dear", "status": "资料分析已验证；真实音频起止与逐字渲染未验证",
            "scope": "只读官方单曲；候选映射由前四句归纳，其他20句作为同曲复核，不能称独立音频真值。",
            "inputs": {"cache": singer.digest(cache_path), "dsc": singer.digest(dsc),
                       "official_db": singer.digest(OFFICIAL_DB), "opcode_db": singer.digest(opcode),
                       "ruby_audit": singer.digest(audit_path), "reader": singer.digest(Path(singer.extractor.__file__)),
                       "observer": singer.digest(Path(singer.__file__)), "research_script": singer.digest(Path(__file__))},
            "candidate_pose_classes": POSE_CLASSES, "baseline_pose": 28,
            "command_count": len(commands), "mouth_count": len(mouths),
            "pose_counts": dict(Counter(x["params"][2] for x in mouths)),
            "nonblank_line_count": len(rows), "exact_line_count": sum(x["exact_class_sequence"] for x in rows),
            "held_out_exact_line_count": sum(x["exact_class_sequence"] for x in rows[4:]),
            "same_pv_difficulties": comparisons, "first_line_candidate_anchors": anchors, "rows": rows,
            "commands": commands}


def write_report(report: dict, output: Path) -> None:
    """写入完整证据、中文逐句表和首句候选锚点，明确不将命令时间当真实发声时间。"""
    output.mkdir(parents=True, exist_ok=True)
    (output / "evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# PV045《Dear》逐句元音与口型核对", "", "O/U仅在口型类别上归并；不补促音、不补尾音、不强行移动边界。编辑距离不是音频误差或准确率。", "",
             "| 有效行 | 原歌词ID | 日文 | 读音元音数 | 口型数 | 完全同序 | 编辑距离 |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in report["rows"]:
        lines.append(f"| {row['runtime_line']} | {row['lyric_id']} | {row['text']} | {len(row['expected_vowels'])} | {len(row['vowel_events'])} | {'是' if row['exact_class_sequence'] else '否'} | {row['alignment']['edit_distance']} |")
    lines += ["", "## 首句逐音候选", "", "下列为脚本命令锚点；真实发声起止未取得。頭的三个读音共用一个正文汉字。", "",
              "| 音序 | 读音 | 对应正文 | 命令秒 | 姿态 | 下个元音命令秒 |", "| --- | --- | --- | --- | --- | --- |"]
    tsv = ["序号\t假名\t正文起点\t正文长度\t正文\t命令毫秒\t下一元音命令毫秒\t真实发声终点"]
    for item in report["first_line_candidate_anchors"]:
        next_ms = item["next_vowel_command_ms"]
        next_seconds = f"{next_ms / 1000:.5f}" if next_ms is not None else "未知"
        lines.append(f"| {item['number']} | {item['kana']} | {item['text']} | {item['command_ms'] / 1000:.5f} | {item['pose']} | {next_seconds} |")
        tsv.append(f"{item['number']}\t{item['kana']}\t{item['text_start']}\t{item['text_length']}\t{item['text']}\t{item['command_ms']:.2f}\t{next_ms if next_ms is not None else '未知'}\t未知")
    (output / "逐句核对.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "首句候选锚点.tsv").write_text("\n".join(tsv) + "\n", encoding="utf-8")


def main() -> int:
    """执行限定单曲的只读研究并用中文报告结果。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_arguments()
    try:
        report = build_report(args.cache, args.verify_difficulties)
        write_report(report, args.output_dir)
    except (OSError, ValueError, KeyError) as error:
        print(f"研究失败：{error}", file=sys.stderr)
        return 1
    print(f"研究完成：《Dear》{report['nonblank_line_count']}句，{report['mouth_count']}条口型。")
    print(f"元音类别完全同序：{report['exact_line_count']}句；其余行保留差异，不发布正式逐字时间。")
    print(f"首句输出{len(report['first_line_candidate_anchors'])}个候选锚点；真实发声终点仍未知。")
    print(f"结果目录：{args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
