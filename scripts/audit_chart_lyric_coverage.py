#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计 Charts Pack 谱面与已生成原生歌词缓存的逻辑歌曲覆盖关系。"""

import argparse
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


NORMAL_DSC_PATTERN = re.compile(r"^pv_(\d+)_normal\.dsc$", re.IGNORECASE)


def parse_arguments() -> argparse.Namespace:
    """解析 Charts Pack 审计所需的输入、缓存与报告路径。"""
    parser = argparse.ArgumentParser(description="审计 Charts Pack 的歌曲映射与原生歌词缓存覆盖。")
    parser.add_argument("--chart-root", type=Path, required=True, help="Charts Pack 的 rom 目录。")
    parser.add_argument("--chart-map", type=Path, required=True, help="Charts Pack 的 nc_db.toml 映射表。")
    parser.add_argument("--cache-dir", type=Path, required=True, help="已部署或汇总后的 PVxxx.srt 缓存目录。")
    parser.add_argument("--opcode-db", type=Path, required=True, help="Open-PD-Script-Editor 的 opcode_db/db.json 文件。")
    parser.add_argument("--extractor", type=Path, default=Path("scripts/extract_native_lyric_timeline.py"), help="歌词 DSC 读取模块路径。")
    parser.add_argument("--report", type=Path, required=True, help="输出 UTF-8 JSON 审计报告文件。")
    return parser.parse_args()


def load_extractor(extractor_path: Path):
    """动态加载既有歌词读取器，避免在审计脚本重复实现 DSC 解析。"""
    specification = importlib.util.spec_from_file_location("native_lyric_extractor", extractor_path)
    if specification is None or specification.loader is None:
        raise ValueError(f"无法加载歌词读取器：{extractor_path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_chart_mapping(chart_map_path: Path) -> dict[int, int]:
    """读取 nc_db.toml 的歌曲 ID 与 Console Normal 谱面编号映射。"""
    document = tomllib.loads(chart_map_path.read_text(encoding="utf-8"))
    mapping: dict[int, int] = {}
    for song in document.get("songs", []):
        logical_pv_id = song.get("id")
        if not isinstance(logical_pv_id, int):
            continue
        for normal_entry in song.get("normal", []):
            script_file_name = normal_entry.get("script_file_name")
            if not isinstance(script_file_name, str):
                continue
            match = NORMAL_DSC_PATTERN.match(Path(script_file_name).name)
            if match is None:
                continue
            physical_pv_id = int(match.group(1))
            existing = mapping.get(physical_pv_id)
            if existing is not None and existing != logical_pv_id:
                raise ValueError(f"谱面 PV{physical_pv_id:03d} 映射到多个歌曲 ID：{existing} 与 {logical_pv_id}。")
            mapping[physical_pv_id] = logical_pv_id
    if not mapping:
        raise ValueError("nc_db.toml 中未找到 Console Normal 谱面映射。")
    return mapping


def discover_chart_scripts(chart_root: Path) -> dict[int, Path]:
    """发现 Charts Pack 中所有 Normal 谱面脚本，并检查编号是否重复。"""
    scripts: dict[int, Path] = {}
    for path in chart_root.rglob("pv_*_normal.dsc"):
        match = NORMAL_DSC_PATTERN.match(path.name)
        if match is None:
            continue
        physical_pv_id = int(match.group(1))
        if physical_pv_id in scripts:
            raise ValueError(f"谱面 PV{physical_pv_id:03d} 出现重复文件：{scripts[physical_pv_id]} 与 {path}。")
        scripts[physical_pv_id] = path
    if not scripts:
        raise ValueError("Charts Pack 中未找到任何 Normal 谱面脚本。")
    return scripts


def choose_dsc_format(dsc_path: Path) -> str:
    """依据文件魔数选择 F 或 PVSC 头的 F2 谱面读取格式。"""
    magic = dsc_path.read_bytes()[:4]
    if magic == b"PVSC":
        return "f2pvsc"
    return "f"


def main() -> int:
    """验证每份 Charts 谱面无歌词事件且其逻辑歌曲已有正式 SRT。"""
    arguments = parse_arguments()
    try:
        extractor = load_extractor(arguments.extractor)
        if not arguments.opcode_db.is_file() or not arguments.cache_dir.is_dir():
            raise ValueError("opcode 数据库或歌词缓存目录不存在。")
        mapping = load_chart_mapping(arguments.chart_map)
        scripts = discover_chart_scripts(arguments.chart_root)
        opcode_lengths = {format_name: extractor.load_opcode_lengths(arguments.opcode_db, format_name) for format_name in ("f", "f2pvsc")}
        report = {"schema_version": 1, "chart_root": str(arguments.chart_root), "chart_map": str(arguments.chart_map), "cache_dir": str(arguments.cache_dir), "covered": [], "unreferenced": [], "failed": []}
        for physical_pv_id, dsc_path in sorted(scripts.items()):
            logical_pv_id = mapping.get(physical_pv_id)
            if logical_pv_id is None:
                report["unreferenced"].append({"chart_pv_id": physical_pv_id, "dsc": str(dsc_path), "reason": "nc_db.toml 未声明此 Normal 谱面，游戏不会将其作为可选歌曲加载。"})
                continue
            dsc_format = choose_dsc_format(dsc_path)
            events, _ = extractor.read_lyric_events(dsc_path, opcode_lengths[dsc_format], dsc_format)
            if events:
                report["failed"].append({"chart_pv_id": physical_pv_id, "pv_id": logical_pv_id, "error": f"Charts 谱面意外包含 {len(events)} 条 LYRIC 事件，必须另建歌词来源。"})
                continue
            cache_path = arguments.cache_dir / f"PV{logical_pv_id}.srt"
            if not cache_path.is_file():
                report["failed"].append({"chart_pv_id": physical_pv_id, "pv_id": logical_pv_id, "error": "逻辑歌曲缺少正式 SRT 缓存。"})
                continue
            report["covered"].append({"chart_pv_id": physical_pv_id, "pv_id": logical_pv_id, "dsc": str(dsc_path), "dsc_format": dsc_format, "cache": str(cache_path)})
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Charts 审计完成：覆盖 {len(report['covered'])}，未引用 {len(report['unreferenced'])}，失败 {len(report['failed'])}。报告：{arguments.report}")
        return 0 if not report["failed"] else 1
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"Charts 审计失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
