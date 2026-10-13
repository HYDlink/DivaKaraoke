#!/usr/bin/env python3
"""将指定曲目的歌词与 Ruby 平假名注音整理成人类可读的校对稿。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
KANJI_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]")


def parse_pv_id(value: str) -> int:
    """解析数字编号或 PV 前缀编号，统一转成整数。"""
    normalized = value.strip().upper()
    if normalized.startswith("PV"):
        normalized = normalized[2:]
    try:
        pv_id = int(normalized, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"无效的 PV 编号：{value}") from error
    if pv_id < 0:
        raise argparse.ArgumentTypeError(f"PV 编号不能为负数：{value}")
    return pv_id


def format_timestamp(milliseconds: int) -> str:
    """将毫秒转换为校对稿使用的分秒毫秒格式。"""
    minutes, remaining = divmod(milliseconds, 60_000)
    seconds, fraction = divmod(remaining, 1_000)
    return f"{minutes:02d}:{seconds:02d}.{fraction:03d}"


@lru_cache(maxsize=8)
def load_song_titles(source_path: str) -> dict[int, str]:
    """读取并缓存文本数据库中的歌曲标题，避免全量导出时重复扫描。"""
    path = Path(source_path)
    titles: dict[int, str] = {}
    if not path.is_file():
        return titles
    pattern = re.compile(r"^pv_(\d+)\.song_name=(.*)$")
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(raw_line)
        if match:
            titles[int(match.group(1))] = match.group(2).strip()
    return titles


def find_song_title(timeline: dict, pv_id: int) -> str:
    """从时间线记录的官方文本表中读取歌曲标题，缺失时返回 PV 编号。"""
    for source_path in timeline.get("source", {}).get("pv_db", []):
        title = load_song_titles(str(source_path)).get(pv_id)
        if title:
            return title
    return f"PV{pv_id:03d}"


def annotate_text(text: str, spans: list[dict]) -> tuple[str, list[str]]:
    """按 Unicode 字符位置将注音嵌入歌词，并报告越界或覆盖异常。"""
    output: list[str] = []
    warnings: list[str] = []
    covered: set[int] = set()
    cursor = 0
    for span in sorted(spans, key=lambda item: int(item.get("start", -1))):
        start = int(span.get("start", -1))
        length = int(span.get("length", 0))
        reading = str(span.get("ruby", ""))
        if start < 0 or length <= 0 or start + length > len(text):
            warnings.append(f"注音跨度 {start}:{length} 超出歌词长度 {len(text)}，未嵌入显示")
            continue
        if start < cursor:
            warnings.append(f"注音跨度 {start}:{length} 与前一个跨度重叠")
            continue
        if start > cursor:
            output.append(text[cursor:start])
        base = text[start:start + length]
        if any(not KANJI_PATTERN.fullmatch(char) for char in base):
            warnings.append(f"注音跨度 {start}:{length} 覆盖了非汉字内容：{base}")
        output.append(f"{base}《{reading}》")
        covered.update(range(start, start + length))
        cursor = start + length
    output.append(text[cursor:])
    uncovered = [index for index, char in enumerate(text)
                 if KANJI_PATTERN.fullmatch(char) and index not in covered]
    if uncovered:
        warnings.append("未带注音的汉字位置：" + ", ".join(map(str, uncovered)))
    return "".join(output), warnings


def load_song(cache_dir: Path, pv_id: int) -> tuple[str, int, int]:
    """读取并核对单曲时间线和 Ruby 审计，返回校对稿与统计信息。"""
    prefix = f"PV{pv_id:03d}"
    timeline_path = cache_dir / f"{prefix}.json"
    tsv_path = cache_dir / f"{prefix}.ruby.tsv"
    audit_path = cache_dir / f"{prefix}.ruby.audit.json"
    for path in (timeline_path, tsv_path, audit_path):
        if not path.is_file():
            raise FileNotFoundError(f"缺少文件：{path}")
    timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    if int(timeline.get("pv_id", -1)) != pv_id or int(audit.get("pvId", -1)) != pv_id:
        raise ValueError(f"{prefix} 的 PV 编号与文件名不一致")
    timeline_lines = timeline.get("lines", [])
    audit_rows = audit.get("rows", [])
    if len(timeline_lines) != len(audit_rows):
        raise ValueError(f"{prefix} 时间线与注音审计行数不一致")
    tsv_spans: dict[int, list[tuple[int, int, str]]] = {}
    for raw_line in tsv_path.read_text(encoding="utf-8-sig").splitlines():
        if not raw_line or raw_line.startswith("#"):
            continue
        row_number, separator, encoded = raw_line.partition("\t")
        if not separator:
            raise ValueError(f"{prefix} Ruby TSV 行缺少制表符：{raw_line}")
        parsed: list[tuple[int, int, str]] = []
        if encoded:
            for entry in encoded.split(";"):
                start, first_separator, remainder = entry.partition(":")
                length, second_separator, reading = remainder.partition(":")
                if not first_separator or not second_separator:
                    raise ValueError(f"{prefix} Ruby TSV 格式错误：{entry}")
                parsed.append((int(start), int(length), reading))
        number = int(row_number)
        if number in tsv_spans:
            raise ValueError(f"{prefix} Ruby TSV 重复行号：{number}")
        tsv_spans[number] = parsed

    title = find_song_title(timeline, pv_id)
    output = [f"# {prefix}《{title}》歌词与平假名注音校对稿", ""]
    output.append("注音以 `汉字《ひらがな》` 形式紧跟在对应汉字后。")
    output.append("本稿逐项展示现有 Ruby TSV 的位置与读音，便于人工核对。自动提示只检查结构、汉字覆盖和原有审计理由，不会判断读音的语义是否正确，必须对照日语歌词人工确认。")
    output.append("")
    expected_runtime_rows = {int(row["runtime_index"]) for row in audit_rows if row.get("runtime_index") is not None}
    if set(tsv_spans) != expected_runtime_rows:
        raise ValueError(f"{prefix} Ruby TSV 行号与审计有效行号不一致")
    annotated_count = 0
    warning_count = 0
    for position, (line, row) in enumerate(zip(timeline_lines, audit_rows), start=1):
        text = str(line.get("text", ""))
        audit_text = str(row.get("japanese", ""))
        if text != audit_text:
            raise ValueError(f"{prefix} 第 {position} 行：时间线文本与注音审计不一致")
        spans = row.get("spans", [])
        expected_spans = [(int(span["start"]), int(span["length"]), str(span["ruby"]))
                          for span in spans]
        runtime_index = row.get("runtime_index")
        actual_spans = tsv_spans.get(int(runtime_index), []) if runtime_index is not None else []
        if actual_spans != expected_spans:
            raise ValueError(f"{prefix} 第 {position} 行：Ruby TSV 与注音审计不一致")
        annotated, warnings = annotate_text(text, spans)
        start_time = format_timestamp(int(line["start_ms"]))
        end_time = format_timestamp(int(line["end_ms"]))
        output.append(f"## 行 {position}（lyric ID {line.get('lyric_id', '?')}，{start_time}–{end_time}）")
        output.append("")
        if text:
            output.append(f"**歌词与注音：** {annotated}")
        else:
            output.append("**歌词与注音：** （空行）")
        if spans:
            annotated_count += len(spans)

        else:
            output.append("**注音：** 无")
        output.append(f"**来源罗马音：** {row.get('romaji') or '（无）'}")
        if row.get("reading_strategy"):
            output.append(f"**读音依据：** {row['reading_strategy']}")
        if row.get("alignment"):
            alignment = row["alignment"]
            state = {"aligned":"完整对齐", "ambiguous":"存在切分歧义", "unmatched":"无法完整对齐", "missing":"来源唱法缺失"}.get(alignment["status"],alignment["status"])
            output.append(f"**对齐状态：** {state}")
        for reason in row.get("review_reasons", []):
            warnings.append(str(reason))
        if warnings:
            warning_count += 1
            output.append("**校对提示：** " + "；".join(warnings))
        output.append("")
    output.insert(3, f"共 {len(audit_rows)} 行，{annotated_count} 个注音跨度，{warning_count} 行含结构/审计提示。")
    return "\n".join(output) + "\n", annotated_count, warning_count


def collect_pv_ids(cache_dir: Path, requested: list[int], export_all: bool) -> list[int]:
    """根据用户选择的编号或全部选项收集可用单曲。"""
    if export_all:
        return sorted(int(path.stem[2:]) for path in cache_dir.glob("PV*.json")
                      if re.fullmatch(r"PV\d+", path.stem)
                      and (cache_dir / f"{path.stem}.ruby.audit.json").is_file())
    return sorted(set(requested))


def parse_arguments() -> argparse.Namespace:
    """解析缓存目录、PV 编号、全量选项和校对稿输出目录。"""
    parser = argparse.ArgumentParser(
        description="按 PV 编号导出歌词与平假名注音的人类可读校对稿",
        epilog="编号可写 253 或 PV253；--pv-id 可重复使用，也可一次提供多个编号。",
    )
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "artifacts/full-export-deployment/cache",
                        help="包含 PVxxx.json 与 PVxxx.ruby.audit.json 的缓存目录")
    parser.add_argument("--pv-id", type=parse_pv_id, action="append", nargs="+", default=[],
                        help="要导出的 PV 编号；可重复指定或一次给出多个编号")
    parser.add_argument("--all", action="store_true", help="导出缓存目录内全部有注音审计的 PV")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/ruby-review",
                        help="校对稿输出目录")
    arguments = parser.parse_args()
    arguments.pv_ids = [pv_id for group in arguments.pv_id for pv_id in group]
    if not arguments.all and not arguments.pv_ids:
        parser.print_help()
        raise SystemExit("请使用 --pv-id 指定编号，或使用 --all 导出全部。")
    if arguments.all and arguments.pv_ids:
        raise SystemExit("--all 与 --pv-id 不能同时使用。")
    return arguments


def main() -> int:
    """导出单曲校对稿和可点击的索引文件，并用中文报告结果。"""
    arguments = parse_arguments()
    cache_dir = arguments.cache_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    if not cache_dir.is_dir():
        print(f"缓存目录不存在：{cache_dir}", file=sys.stderr)
        return 2
    pv_ids = collect_pv_ids(cache_dir, arguments.pv_ids, arguments.all)
    if not pv_ids:
        print("没有找到可导出的 PV 文件。", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# 歌词与平假名注音校对稿索引", "", "点击 PV 编号查看对应歌词、注音、罗马音和校对提示。", ""]
    exported = 0
    try:
        for pv_id in pv_ids:
            document, span_count, warning_count = load_song(cache_dir, pv_id)
            filename = f"PV{pv_id:03d}.md"
            (output_dir / filename).write_text(document, encoding="utf-8")
            title = find_song_title(json.loads((cache_dir / f"PV{pv_id:03d}.json").read_text(encoding="utf-8-sig")), pv_id)
            index_lines.append(f"- [PV{pv_id:03d}《{title}》]({filename})：{span_count} 个注音跨度，{warning_count} 行含提示")
            exported += 1
            if not arguments.all:
                print(f"已导出 PV{pv_id:03d}：{span_count} 个注音跨度，{warning_count} 行含提示。")
            elif exported % 25 == 0:
                print(f"已处理 {exported}/{len(pv_ids)} 首。")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"导出失败：{error}", file=sys.stderr)
        return 1
    index_path = output_dir / "README.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"共导出 {exported} 首；索引文件：{index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
