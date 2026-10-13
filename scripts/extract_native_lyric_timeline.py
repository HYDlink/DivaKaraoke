#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已提取的 Future Tone DSC 与 PV 文本表生成单曲行级歌词时间线。"""

import argparse
import json
import re
import struct
import sys
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# Future Tone 的时间单位：每秒 100000 个单位。
TIME_UNITS_PER_SECOND = 100_000
TIME_OPCODE = 1
LYRIC_OPCODE = 24
PV_END_OPCODE = 32
FORMAT_DATABASE_KEYS = {"ft": "info_FT", "f": "info_f", "f2": "info_F2", "f2pvsc": "info_F2"}
FORMAT_HEADER_SIZES = {"ft": 4, "f": 4, "f2": 72, "f2pvsc": 68}
F2_EOFC_OPCODE = 1128681285


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数，并限制工具只处理一首指定 PV。"""
    parser = argparse.ArgumentParser(
        description="使用 Open-PD-Script-Editor 的 Future Tone opcode 表生成原生行级歌词时间线。"
    )
    parser.add_argument("--pv-id", type=int, required=True, help="要处理的 PV 编号，例如 424。")
    parser.add_argument("--dsc", type=Path, required=True, help="已从官方 CPK 提取的 Future Tone DSC 文件。")
    parser.add_argument("--pv-db", type=Path, action="append", required=True, help="已提取的 pv_db、mdata_pv_db 或 mod_pv_db 文本文件；可重复指定。")
    parser.add_argument("--allow-lyric-overrides", action="store_true", help="多个文本表冲突时保留最先指定的文本，仅用后续文本表补缺失 ID。")
    parser.add_argument("--opcode-db", type=Path, required=True, help="Open-PD-Script-Editor 的 opcode_db/db.json 文件。")
    parser.add_argument("--dsc-format", choices=FORMAT_DATABASE_KEYS, default="ft", help="DSC 格式：ft、f、f2 或 f2pvsc；默认 ft。")
    # 输出结果文件参数：保存可审计的原生歌词 JSON 时间线。
    parser.add_argument("--out-json", type=Path, required=True, help="输出的 UTF-8 JSON 时间线文件。")
    # 输出结果文件参数：保存供现有 SRT 加载路径立即验证的原生派生缓存。
    parser.add_argument("--out-srt", type=Path, required=True, help="输出的 UTF-8 SRT 验证缓存文件。")
    return parser.parse_args()


def load_opcode_lengths(opcode_db_path: Path, dsc_format: str) -> dict[int, int]:
    """读取既有 Open-PD 指定 DSC 格式的 opcode 参数长度表。"""
    database = json.loads(opcode_db_path.read_text(encoding="utf-8"))
    lengths: dict[int, int] = {}
    format_key = FORMAT_DATABASE_KEYS[dsc_format]
    for command in database.values():
        info = command.get(format_key)
        if info is not None:
            lengths[int(info["id"])] = int(info["len"])
    if lengths.get(TIME_OPCODE) != 1 or lengths.get(LYRIC_OPCODE) != 2:
        raise ValueError(f"{dsc_format} opcode 表未包含预期的 TIME 或 LYRIC 定义。")
    return lengths


def load_lyrics(pv_db_paths: list[Path], pv_id: int, allow_overrides: bool) -> dict[int, str]:
    """读取多个歌词文本表；显式允许时保留首表版本并由后表补缺失 ID。"""
    pattern = re.compile(rf"^pv_{pv_id:03d}\.lyric\.(\d+)=(.*)$")
    lyrics: dict[int, str] = {}
    for pv_db_path in pv_db_paths:
        for raw_line in pv_db_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(raw_line)
            if match:
                lyric_id, text = int(match.group(1)), match.group(2)
                existing = lyrics.get(lyric_id)
                if existing is not None and existing != text and not allow_overrides:
                    raise ValueError(f"歌词 ID {lyric_id} 在多个文本表中存在冲突。")
                if existing is None:
                    lyrics[lyric_id] = text
    if not lyrics:
        raise ValueError(f"文本数据库中未找到 PV{pv_id:03d} 的歌词键。")
    return lyrics


def read_lyric_events(dsc_path: Path, opcode_lengths: dict[int, int], dsc_format: str) -> tuple[list[tuple[int, int]], int | None]:
    """按既有 Open-PD 格式规则读取 TIME、LYRIC 与 PV_END。"""
    data = dsc_path.read_bytes()
    header_size = FORMAT_HEADER_SIZES[dsc_format]
    if len(data) < header_size:
        raise ValueError("DSC 文件短于对应格式的文件头。")

    offset = header_size
    current_time = 0
    events: list[tuple[int, int]] = []
    pv_end_time: int | None = None
    command_count = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"DSC 在偏移 {offset} 处出现不完整 opcode。")
        opcode = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if dsc_format in {"f2", "f2pvsc"} and opcode == F2_EOFC_OPCODE:
            break
        parameter_count = opcode_lengths.get(opcode)
        if parameter_count is None:
            raise ValueError(f"DSC 在命令 {command_count} 使用未知 Future Tone opcode：{opcode}。")
        parameter_end = offset + parameter_count * 4
        if parameter_end > len(data):
            raise ValueError(f"DSC 在命令 {command_count} 的参数区不完整。")
        parameters = struct.unpack_from(f"<{parameter_count}i", data, offset)
        offset = parameter_end
        command_count += 1
        if opcode == TIME_OPCODE:
            current_time = parameters[0]
        elif opcode == LYRIC_OPCODE:
            events.append((current_time, parameters[0]))
        elif opcode == PV_END_OPCODE:
            pv_end_time = current_time
    return events, pv_end_time


def merge_short_duplicate_lines(lines: list[dict[str, int | str]], max_gap_ms: int = 250) -> list[dict[str, int | str]]:
    """合并相邻同 ID 同文本且间隔不超过阈值的事件，不再限制歌词段长度。"""
    merged: list[dict[str, int | str]] = []
    for line in lines:
        gap_ms = int(line["start_ms"]) - int(merged[-1]["end_ms"]) if merged else max_gap_ms + 1
        if (merged and -100 <= gap_ms <= max_gap_ms
                and merged[-1]["lyric_id"] == line["lyric_id"]
                and merged[-1]["text"] == line["text"]):
            merged[-1]["end_ms"] = max(int(merged[-1]["end_ms"]), int(line["end_ms"]))
            if "end_source" in line:
                merged[-1]["end_source"] = line["end_source"]
            continue
        merged.append(dict(line))
    return merged

def build_lines(events: list[tuple[int, int]], lyrics: dict[int, str], pv_end_time: int | None) -> list[dict[str, int | str]]:
    """合并歌词并用下一事件或官方 PV_END 命令闭合每一行的结束时间。"""
    lines: list[dict[str, int | str]] = []
    active_line: dict[str, int | str] | None = None
    for raw_time, lyric_id in events:
        timestamp_ms = raw_time // 100
        if active_line is not None:
            active_line["end_ms"] = timestamp_ms
            lines.append(active_line)
            active_line = None
        # 原生 LYRIC(0/-1) 表示隐藏/清屏；其时间已用于上一句收尾，不生成虚假歌词行。
        if lyric_id <= 0:
            continue
        text = lyrics.get(lyric_id)
        if text is None:
            raise ValueError(f"歌词事件 ID {lyric_id} 在文本数据库中没有对应项。")
        active_line = {
            "start_ms": timestamp_ms,
            "end_ms": timestamp_ms,
            "text": text,
            "lyric_id": lyric_id,
            "raw_time": raw_time,
        }
    if active_line is not None:
        if pv_end_time is None:
            raise ValueError("最后一条歌词事件没有后续歌词、清屏或 PV_END 事件，无法得到可靠结束时间。")
        terminal_end_ms = pv_end_time // 100
        if terminal_end_ms <= int(active_line["start_ms"]):
            raise ValueError("PV_END 时间不晚于最后一条歌词开始时间，无法得到可靠结束时间。")
        active_line["end_ms"] = terminal_end_ms
        active_line["end_source"] = "pv_end"
        lines.append(active_line)
    if not lines:
        raise ValueError("没有生成可闭合的非空歌词行。")
    return merge_short_duplicate_lines(lines)


def format_srt_timestamp(timestamp_ms: int) -> str:
    """将毫秒格式化为现有 SRT 加载器可读取的时间戳。"""
    hours, remainder = divmod(timestamp_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_outputs(lines: list[dict[str, int | str]], arguments: argparse.Namespace) -> None:
    """写出 JSON 审计产物和现有运行时可直接加载的原生派生 SRT 缓存。"""
    arguments.out_json.parent.mkdir(parents=True, exist_ok=True)
    arguments.out_srt.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": 1,
        "pv_id": arguments.pv_id,
        "source": {
            "dsc": str(arguments.dsc),
            "pv_db": [str(path) for path in arguments.pv_db],
            "opcode_db": str(arguments.opcode_db),
            "time_unit": "1/100000 second",
        },
        "lines": lines,
    }
    arguments.out_json.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    srt_blocks = []
    for index, line in enumerate(lines, start=1):
        srt_blocks.append(
            f"{index}\n"
            f"{format_srt_timestamp(int(line['start_ms']))} --> "
            f"{format_srt_timestamp(int(line['end_ms']))}\n"
            f"{line['text']}"
        )
    # 末尾保留空白分隔行，确保现有 SubRipParser 在换行结尾时也提交最后一条字幕。
    arguments.out_srt.write_text("\n\n".join(srt_blocks) + "\n\n", encoding="utf-8")


def main() -> int:
    """执行单曲原生时间线提取，并以中文输出可审计的结果。"""
    arguments = parse_arguments()
    try:
        opcode_lengths = load_opcode_lengths(arguments.opcode_db, arguments.dsc_format)
        events, pv_end_time = read_lyric_events(arguments.dsc, opcode_lengths, arguments.dsc_format)
        if not any(lyric_id > 0 for _, lyric_id in events):
            raise ValueError("DSC 中未读取到任何 LYRIC 事件。")
        lyrics = load_lyrics(arguments.pv_db, arguments.pv_id, arguments.allow_lyric_overrides)
        lines = build_lines(events, lyrics, pv_end_time)
        write_outputs(lines, arguments)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"提取失败：{error}", file=sys.stderr)
        return 1
    print(f"提取成功：PV{arguments.pv_id:03d}，歌词事件 {len(events)} 条，已闭合歌词行 {len(lines)} 条。")
    print(f"JSON 时间线：{arguments.out_json}")
    print(f"SRT 验证缓存：{arguments.out_srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
