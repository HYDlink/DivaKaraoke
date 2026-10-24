#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复用已解析资产研究《愛Dee》的角色口型、字幕边界和双人参与证据。"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import research_pv041_mouth as common

ROOT = Path(__file__).resolve().parents[1]
PV_ID = 802


def parse_arguments() -> argparse.Namespace:
    """读取限定PV802的研究参数，不支持曲库扫描、解包、安装或运行时配色。"""
    parser = argparse.ArgumentParser(description="调查愛Dee已提取口型与现有歌词时间线的关系。")
    # 缓存输入参数：从既有PV802缓存获取真实来源，不猜测歌曲编号与资产路径。
    parser.add_argument("--cache", type=Path, default=ROOT / "artifacts/furigana-official-alignment/cache/PV802.json", help="已有PV802歌词JSON缓存。")
    # 输出结果目录参数：只写研究证据和中文逐句统计，不覆盖生产缓存。
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/pv802-mouth-research", help="UTF-8研究产物输出目录。")
    # 难度检查参数：只比较同一首歌的已存在难度，不扩展其他歌曲。
    parser.add_argument("--verify-other-difficulties", action="store_true", help="比较同曲其他三个难度的完整口型序列。")
    return parser.parse_args()


def read_fields(paths: list[Path]) -> dict:
    """逐来源记录本曲角色、曲名、脚本映射与罗马音，避免把Mod表当官方表。"""
    pattern = re.compile(r"^pv_802\.(performer\..+|song_name|difficulty\..+script_file_name|lyric_en\.\d+)=(.*)$")
    return {
        str(path.resolve()): {
            match.group(1): match.group(2)
            for line in path.read_text(encoding="utf-8").splitlines()
            if (match := pattern.match(line))
        }
        for path in paths
    }


def read_pose_reference() -> tuple[dict[int, str], int, dict]:
    """从已有Open-PD头文件读取元音映射，未知姿态保持未知，不凭样本手工加规则。"""
    path = ROOT / "artifacts/Open-PD-Script-Editor/lipsync.h"
    entries = dict(re.findall(r"const int mouth_ft_([aiueom])\s*=\s*(\d+)\s*;", path.read_text(encoding="utf-8")))
    if set(entries) != set("aiueom"):
        raise ValueError("现有工具的口型参考表不完整，不能猜测姿态含义。")
    vowels = {int(entries[letter]): letter.upper() for letter in "aiueo"}
    return vowels, int(entries["m"]), common.file_evidence(path)


def window_statistics(mouths: list[dict], line: dict, vowels: dict[int, str], margin_ms: int) -> dict:
    """计算歌词窗口内已知元音事件；裁边仅作敏感性比较，不输出确定歌手。"""
    start = (int(line["start_ms"]) + margin_ms) * 100
    end = (int(line["end_ms"]) - margin_ms) * 100
    entries = [event for event in mouths if start <= event["raw_time"] < end]
    slots = {}
    for slot in (0, 1):
        selected = [event for event in entries if event["params"][0] == slot]
        vowel_events = [event for event in selected if event["params"][2] in vowels]
        slots[str(slot)] = {
            "event_count": len(selected),
            "vowel_event_count": len(vowel_events),
            "pose_counts": dict(Counter(event["params"][2] for event in selected)),
            "vowel_command_indices": [event["index"] for event in vowel_events],
            "first_vowel_event_ms": vowel_events[0]["time_ms"] if vowel_events else None,
            "last_vowel_event_ms": vowel_events[-1]["time_ms"] if vowel_events else None,
        }
    return {"margin_ms": margin_ms, "slots": slots, "slots_with_vowel_events": [slot for slot in (0, 1) if slots[str(slot)]["vowel_event_count"]]}


def build_report(cache_path: Path, verify_difficulties: bool) -> dict:
    """关联现有缓存和已解析命令，记录可自动区分的证据类型与尚不明确的声部。"""
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if cache.get("pv_id") != PV_ID:
        raise ValueError("本研究仅接受愛Dee的PV802缓存。")
    dsc_path = Path(cache["source"]["dsc"])
    db_paths = [Path(path) for path in cache["source"]["pv_db"]]
    fields = read_fields(db_paths)
    if not any(source.get("song_name") == "愛Dee" for source in fields.values()):
        raise ValueError("来源文本表没有确认PV802曲名为愛Dee。")
    commands, lyric_events, pv_end = common.observe_existing_reader(dsc_path)
    lyrics = common.extractor.load_lyrics(db_paths, PV_ID, True)
    rebuilt = common.extractor.build_lines(lyric_events, lyrics, pv_end)
    cache_lines = [line for line in cache["lines"] if line["text"].strip()]
    rebuilt_lines = [line for line in rebuilt if line["text"].strip()]
    comparable_fields = ("start_ms", "end_ms", "lyric_id", "text")
    expected = [tuple(line[key] for key in comparable_fields) for line in cache_lines]
    actual = [tuple(line[key] for key in comparable_fields) for line in rebuilt_lines]
    if actual != expected:
        raise ValueError("来源重新解析的时间线与当前缓存不一致，停止关联。")
    vowels, baseline, pose_reference = read_pose_reference()
    mouths = [command for command in commands if command["name"] == "MOUTH_ANIM"]
    if any(command["name"] in {"EDIT_MOUTH", "EDIT_MOUTH_ANIM"} for command in commands):
        raise ValueError("本样本含隐式角色口型，需要另行复核，不能只统计显式口型。")
    if any(command["branch"] != 0 for command in mouths):
        raise ValueError("本样本口型含非全局分支，需要先区分实际执行条件。")
    if any(first["raw_time"] > second["raw_time"] for first, second in zip(mouths, mouths[1:])):
        raise ValueError("口型时间有回退，不能直接按线性窗口统计。")
    rows = []
    for number, line in enumerate(cache_lines, 1):
        statistics = [window_statistics(mouths, line, vowels, margin) for margin in (0, 100, 200, 300, 500)]
        indices = [event["index"] for event in mouths if int(line["start_ms"]) * 100 <= event["raw_time"] < int(line["end_ms"]) * 100]
        rows.append({"line_number": number, **line, "window_statistics": statistics, "mouth_command_indices": indices})
    outside = [event for event in mouths if not any(int(line["start_ms"]) * 100 <= event["raw_time"] < int(line["end_ms"]) * 100 for line in cache_lines)]
    sensitivity = []
    for index, margin in enumerate((0, 100, 200, 300, 500)):
        distributions = Counter(tuple(row["window_statistics"][index]["slots_with_vowel_events"]) for row in rows)
        sensitivity.append({
            "margin_ms": margin,
            "miku_only": distributions[(0,)],
            "luka_only": distributions[(1,)],
            "both": distributions[(0, 1)],
            "neither": distributions[()],
            "both_line_numbers": [row["line_number"] for row in rows if row["window_statistics"][index]["slots_with_vowel_events"] == [0, 1]],
        })
    comparisons = []
    if verify_difficulties:
        sequence = [(event["raw_time"], event["params"], event["branch"]) for event in mouths]
        for difficulty in ("easy", "hard", "extreme"):
            path = dsc_path.with_name(f"pv_802_{difficulty}.dsc")
            other_commands, _, _ = common.observe_existing_reader(path)
            other = [(event["raw_time"], event["params"], event["branch"]) for event in other_commands if event["name"] == "MOUTH_ANIM"]
            comparisons.append({"difficulty": difficulty, "input": common.file_evidence(path), "mouth_count": len(other), "exactly_matches_normal": sequence == other})
    # 安装SRT只读核对，不能据磁盘一致宣称当前游戏进程已经验证。
    installed_srt = dsc_path.parents[3] / "MMFreeLyrics/lyrics/PV802.srt"
    generated_srt = cache_path.with_suffix(".srt")
    srt_check = None
    if installed_srt.is_file() and generated_srt.is_file():
        srt_check = {"installed": common.file_evidence(installed_srt), "generated": common.file_evidence(generated_srt), "sha256_matches": installed_srt.read_bytes() == generated_srt.read_bytes()}
    return {
        "pv_id": PV_ID,
        "scope": "已安装X Song Pack中的PV802愛Dee；仅单曲研究，不当作官方原版MM+数据。",
        "validation": "完整命令覆盖、LYRIC/PV_END返回核对、48句缓存关联与难度比较；真实音频歌手及主唱/和声角色尚未验证。",
        "inputs": {"cache": common.file_evidence(cache_path), "dsc": common.file_evidence(dsc_path), "pv_db": [common.file_evidence(path) for path in db_paths], "opcode_db": common.file_evidence(common.OPCODE_DB), "existing_reader": common.file_evidence(Path(common.extractor.__file__)), "observer": common.file_evidence(Path(common.__file__))},
        "source_fields": fields,
        "pose_reference": pose_reference,
        "vowel_pose_map": vowels,
        "m_pose": baseline,
        "unknown_pose_ids": sorted({event["params"][2] for event in mouths} - set(vowels) - {baseline}),
        "command_counts": dict(Counter(command["name"] for command in commands)),
        "mouth_by_slot": dict(Counter(event["params"][0] for event in mouths)),
        "mouth_branch_counts": dict(Counter(event["branch"] for event in mouths)),
        "outside_lyric_mouth_commands": outside,
        "pv_end_ms": pv_end / 100 if pv_end is not None else None,
        "lines": rows,
        "boundary_sensitivity": sensitivity,
        "same_pv_difficulty_comparisons": comparisons,
        "installed_srt_check": srt_check,
        "commands": commands,
    }


def write_table(report: dict, path: Path) -> None:
    """输出全部48句中文统计，保留未识别姿态，不用事件数冒充声部正确率。"""
    content = ["# 愛Dee（PV802）口型逐句证据", "", "槽0为初音，槽1为巡音；来源为已安装X Song Pack。元音映射取自现有Open-PD参考，34/35仍未知。", "", "仅统计窗口内指令，不能等同精确演唱区间、主唱身份或正确率。", "", "| 行 | 秒 | 歌词 | 初音事件/元音 | 巡音事件/元音 |", "| --- | --- | --- | --- | --- |"]
    for row in report["lines"]:
        slots = row["window_statistics"][0]["slots"]
        left, right = slots["0"], slots["1"]
        text = row["text"].replace("|", "\\|")
        content.append(f"| {row['line_number']} | {row['start_ms']/1000:.3f}–{row['end_ms']/1000:.3f} | {text} | {left['event_count']}/{left['vowel_event_count']} | {right['event_count']}/{right['vowel_event_count']} |")
    content.extend(["", "## 边界敏感性（仅研究，不设生产阈值）", "", "| 每侧裁边毫秒 | 仅初音元音 | 仅巡音元音 | 两槽元音 | 无元音 |", "| --- | --- | --- | --- | --- |"])
    for item in report["boundary_sensitivity"]:
        content.append(f"| {item['margin_ms']} | {item['miku_only']} | {item['luka_only']} | {item['both']} | {item['neither']} |")
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> int:
    """执行单曲研究并输出中文摘要，不生成运行时歌手标签或修改游戏。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    arguments = parse_arguments()
    try:
        report = build_report(arguments.cache, arguments.verify_other_difficulties)
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        (arguments.output_dir / "evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_table(report, arguments.output_dir / "lines.md")
        print(f"研究完成：愛Dee，{len(report['lines'])}句歌词，{report['command_counts']['MOUTH_ANIM']}条口型指令。")
        print(f"角色口型统计：初音{report['mouth_by_slot'][0]}条，巡音{report['mouth_by_slot'][1]}条。")
        first = report["boundary_sensitivity"][0]
        print(f"窗口内元音证据：仅初音{first['miku_only']}句，仅巡音{first['luka_only']}句，两槽{first['both']}句；不是歌手识别正确率。")
        for item in report["same_pv_difficulty_comparisons"]:
            name = {"easy": "简单", "hard": "困难", "extreme": "极限"}[item["difficulty"]]
            state = "一致" if item["exactly_matches_normal"] else "不同"
            print(f"难度核对：{name}口型与普通难度{state}。")
        print(f"证据目录：{arguments.output_dir.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"研究失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
