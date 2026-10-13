#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仅复核 PV041 已提取资料，记录口型证据，不生成歌手标注或运行时缓存。"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys

import extract_native_lyric_timeline as extractor

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_DSC = Path("F:/DivaKaraOkeLyrics/main-extract/rom/script/pv_041_normal.dsc")
OFFICIAL_DB = ROOT / "artifacts/main-region-extract/rom_steam_region/rom/pv_db.txt"
OPCODE_DB = ROOT / "artifacts/Open-PD-Script-Editor/opcode_db/db.json"


def parse_arguments() -> argparse.Namespace:
    """读取单曲研究参数；不支持扫描曲库、解包或安装。"""
    parser = argparse.ArgumentParser(description="复用现有 DSC 读取函数调查 PV041 的口型与歌词关系。")
    # 输出结果目录参数：仅保存研究 JSON 和逐句统计表，不写游戏目录。
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/pv041-mouth-research", help="研究报告的 UTF-8 输出目录。")
    # 当前覆盖缓存参数：读取缓存来源，核对同曲覆盖脚本，默认仅调查官方原版。
    parser.add_argument("--active-cache", type=Path, help="已生成的 PV041.json，用于比较当前覆盖来源。")
    # 难度核对参数：只比较同一官方 PV 的三个其他难度，不扫描其他歌曲。
    parser.add_argument("--verify-other-difficulties", action="store_true", help="核对官方 Easy、Hard、Extreme 的口型序列。")
    return parser.parse_args()


def file_evidence(path: Path) -> dict:
    """记录研究输入绝对路径、大小和哈希，便于确认资料来源。"""
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def observe_existing_reader(path: Path) -> tuple[list[dict], list[tuple[int, int]], int | None]:
    """用行跟踪旁观现有读取函数已解析的局部变量，不另写二进制读取器。"""
    source_lines, first_line = inspect.getsourcelines(extractor.read_lyric_events)
    probes = [first_line + index for index, line in enumerate(source_lines) if line.strip() == "if opcode == TIME_OPCODE:"]
    if len(probes) != 1:
        raise ValueError("现有读取函数的观察点已变化，需要复核研究脚本。")
    database = json.loads(OPCODE_DB.read_text(encoding="utf-8"))
    names = {int(value["info_FT"]["id"]): name for name, value in database.items() if "info_FT" in value}
    commands: list[dict] = []
    original_trace = sys.gettrace()

    def observe(frame, event, argument):
        """仅在完整参数已由生产读取函数解码后记录命令与字节偏移。"""
        if frame.f_code is extractor.read_lyric_events.__code__ and event == "line" and frame.f_lineno == probes[0]:
            values = frame.f_locals
            opcode = values["opcode"]
            parameters = list(values["parameters"])
            raw_time = parameters[0] if opcode == extractor.TIME_OPCODE else values["current_time"]
            commands.append({
                "index": values["command_count"],
                "offset": values["offset"] - 4 * (len(parameters) + 1),
                "raw_time": raw_time,
                "time_ms": raw_time / 100,
                "name": names[opcode],
                "params": parameters,
            })
        return observe

    try:
        sys.settrace(observe)
        lyric_events, pv_end = extractor.read_lyric_events(path, extractor.load_opcode_lengths(OPCODE_DB, "ft"), "ft")
    finally:
        sys.settrace(original_trace)
    captured_lyrics = [(command["raw_time"], command["params"][0]) for command in commands if command["name"] == "LYRIC"]
    if captured_lyrics != lyric_events:
        raise ValueError("观察到的歌词命令与现有读取函数结果不一致。")
    if 4 + sum(4 * (1 + len(command["params"])) for command in commands) != path.stat().st_size:
        raise ValueError("命令长度总和没有覆盖 DSC 文件，不能使用不完整证据。")
    captured_end = [command["raw_time"] for command in commands if command["name"] == "PV_END"]
    if not captured_end or captured_end[-1] != pv_end:
        raise ValueError("观察到的 PV_END 与现有读取函数结果不一致。")
    # 保留脚本分支与角色上下文，不将不同分支直接合并成实际演唱状态。
    branch, chara_context = 0, None
    for command in commands:
        if command["name"] == "PV_BRANCH_MODE":
            branch = command["params"][0]
        if command["name"] == "SET_CHARA":
            chara_context = command["params"][0]
        command["branch"] = branch
        command["chara_context"] = chara_context
    return commands, lyric_events, pv_end


def read_performers(paths: list[Path]) -> dict:
    """逐来源保留角色字段，避免覆盖版与官方表混用或隐式过滤 GUEST。"""
    result = {}
    pattern = re.compile(r"^pv_041\.performer\.(.+?)=(.*)$")
    for path in paths:
        result[str(path.resolve())] = {
            match.group(1): match.group(2)
            for line in path.read_text(encoding="utf-8").splitlines()
            if (match := pattern.match(line))
        }
    return result


def analyse_source(label: str, dsc: Path, db_paths: list[Path], reference_pose: int) -> dict:
    """统计原始事件及歌词窗口内的口型证据，不把姿态或事件次数转成歌手结论。"""
    commands, lyric_events, pv_end = observe_existing_reader(dsc)
    lyrics = extractor.load_lyrics(db_paths, 41, len(db_paths) > 1)
    all_lines = extractor.build_lines(lyric_events, lyrics, pv_end)
    # 原版 ID31 的文本为空；保留其收尾时间，但不把它当作演唱歌词。
    lines = [line for line in all_lines if str(line["text"]).strip()]
    mouths = [command for command in commands if command["name"] == "MOUTH_ANIM"]
    rows = []
    for number, line in enumerate(lines, 1):
        in_window = [command for command in mouths if int(line["start_ms"]) * 100 <= command["raw_time"] < int(line["end_ms"]) * 100]
        slots = {}
        for slot in (0, 1):
            slot_commands = [command for command in in_window if command["params"][0] == slot]
            other_poses = [command for command in slot_commands if command["params"][2] != reference_pose]
            slots[str(slot)] = {
                "event_count": len(slot_commands),
                "other_pose_count": len(other_poses),
                "first_other_pose_ms": other_poses[0]["time_ms"] if other_poses else None,
                "last_other_pose_ms": other_poses[-1]["time_ms"] if other_poses else None,
                "branch_counts": dict(Counter(command["branch"] for command in slot_commands)),
            }
        rows.append({"line_number": number, **line, "slots": slots, "mouth_command_indices": [command["index"] for command in in_window]})
    return {
        "label": label,
        "inputs": {"dsc": file_evidence(dsc), "pv_db": [file_evidence(path) for path in db_paths]},
        "performer_fields": read_performers(db_paths),
        "command_count": len(commands),
        "command_counts": dict(Counter(command["name"] for command in commands)),
        "mouth_by_slot": dict(Counter(command["params"][0] for command in mouths)),
        "mouth_pose_counts": dict(Counter(command["params"][2] for command in mouths)),
        "mouth_branch_counts": dict(Counter(command["branch"] for command in mouths)),
        "reference_pose": reference_pose,
        "reference_pose_note": "基准姿态仅用于辅助统计；不等于已证实的闭嘴状态或静音区间。",
        "lyric_events": len(lyric_events),
        "empty_text_lyric_ids": sorted({lyric_id for _, lyric_id in lyric_events if lyric_id > 0 and not lyrics[lyric_id].strip()}),
        "pv_end_ms": pv_end / 100 if pv_end is not None else None,
        "lines": rows,
        "commands": commands,
    }


def write_tables(report: dict, destination: Path) -> None:
    """输出中文逐句统计，显式保留角色事件数量与推测之间的边界。"""
    content = ["# PV041 口型事件逐句统计", "", "仅表示原始指令落入歌词窗口的情况；两槽均有事件不代表整句合唱。", ""]
    for source in report["sources"]:
        pose = source["reference_pose"]
        content.extend([f"## {source['label']}", "", f"基准姿态 {pose} 的含义尚未经游戏画面验证；非基准事件也不能当作音频歌唱标签。", "", "| 行 | 时间（秒） | 歌词 | 槽0事件/非基准 | 槽1事件/非基准 |", "| --- | --- | --- | --- | --- |"])
        for row in source["lines"]:
            left, right = row["slots"]["0"], row["slots"]["1"]
            text = row["text"].replace("|", "\\|")
            content.append(f"| {row['line_number']} | {row['start_ms']/1000:.3f}–{row['end_ms']/1000:.3f} | {text} | {left['event_count']}/{left['other_pose_count']} | {right['event_count']}/{right['other_pose_count']} |")
        content.append("")
    destination.write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> int:
    """生成单曲研究证据并核对现有解析结果，不修改 Mod、输入或已部署缓存。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    arguments = parse_arguments()
    try:
        official = analyse_source("官方原版", OFFICIAL_DSC, [OFFICIAL_DB], 28)
        sources = [official]
        comparisons = []
        if arguments.verify_other_difficulties:
            official_sequence = [(command["raw_time"], command["params"], command["branch"]) for command in official["commands"] if command["name"] == "MOUTH_ANIM"]
            for difficulty in ("easy", "hard", "extreme"):
                path = OFFICIAL_DSC.with_name(f"pv_041_{difficulty}.dsc")
                commands, _, _ = observe_existing_reader(path)
                sequence = [(command["raw_time"], command["params"], command["branch"]) for command in commands if command["name"] == "MOUTH_ANIM"]
                comparisons.append({"difficulty": difficulty, "input": file_evidence(path), "mouth_count": len(sequence), "exactly_matches_normal": sequence == official_sequence})
        if arguments.active_cache:
            cache = json.loads(arguments.active_cache.read_text(encoding="utf-8"))
            if cache.get("pv_id") != 41:
                raise ValueError("当前覆盖输入必须是 PV041 的已有缓存。")
            active = analyse_source("当前生成缓存的覆盖来源", Path(cache["source"]["dsc"]), [Path(path) for path in cache["source"]["pv_db"]], 8)
            expected = [(line["start_ms"], line["end_ms"], line["lyric_id"], line["text"]) for line in cache["lines"] if line["text"].strip()]
            actual = [(line["start_ms"], line["end_ms"], line["lyric_id"], line["text"]) for line in active["lines"]]
            if actual != expected:
                raise ValueError("重新关联的覆盖来源时间线与已有缓存不同，不能混用。")
            active["matches_existing_cache"] = True
            active["cache_input"] = file_evidence(arguments.active_cache)
            sources.append(active)
        report = {
            "scope": "PV041 单曲口型资料研究；不进行音频识别、歌手自动标注、渲染、解包或部署。",
            "validation": "文件全长覆盖、LYRIC/PV_END 与原读取结果一致；音频及游戏画面未验证。",
            "opcode_db": file_evidence(OPCODE_DB),
            "existing_reader": file_evidence(Path(extractor.__file__)),
            "sources": sources,
            "same_pv_difficulty_comparisons": comparisons,
        }
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        (arguments.output_dir / "evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_tables(report, arguments.output_dir / "lines.md")
        for source in sources:
            print(f"研究完成：{source['label']}，{len(source['lines'])}句非空歌词，{source['command_counts'].get('MOUTH_ANIM', 0)}条口型指令。")
        for comparison in comparisons:
            state = "一致" if comparison["exactly_matches_normal"] else "不同"
            print(f"同曲难度核对：{comparison['difficulty']}，口型序列与 Normal {state}。")
        print(f"研究证据目录：{arguments.output_dir.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"研究失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
