#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成并校验已提取 DIVA 原生歌词缓存，可选复用 FarcPack 解包 CPK。"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PV_DSC_PATTERN = re.compile(r"^pv_(\d+)_normal\.dsc$", re.IGNORECASE)


def parse_arguments() -> argparse.Namespace:
    """解析全量缓存生成、可选解包与报告输出参数。"""
    parser = argparse.ArgumentParser(description="从已提取资料批量生成 DIVA 原生歌词 JSON/SRT 缓存。")
    parser.add_argument("--extracted-rom", type=Path, required=True, help="已提取包内的 rom 目录，目录下应有 script 子目录。")
    parser.add_argument("--script-dir", type=Path, help="可选的 DSC 目录；Charts Pack 使用 script_nc 时显式指定。")
    parser.add_argument("--script-map-db", type=Path, action="append", help="可选 pv_db 或 mod_pv_db；用于按 Normal script_file_name 映射逻辑 PVID，可重复指定。")
    parser.add_argument("--script-search-root", type=Path, action="append", help="可选的全资源搜索根目录；按文本表声明的 DSC 文件名定位，可重复指定。")
    parser.add_argument("--pv-db", type=Path, action="append", required=True, help="与该资料包匹配的 pv_db、mdata_pv_db 或 mod_pv_db；可重复指定。")
    parser.add_argument("--allow-lyric-overrides", action="store_true", help="多个文本表冲突时保留最先指定的文本，仅用后续表补缺失 ID。")
    parser.add_argument("--opcode-db", type=Path, required=True, help="Open-PD-Script-Editor 的 Future Tone opcode 数据库。")
    parser.add_argument("--dsc-format", choices=("ft", "f", "f2", "f2pvsc"), default="ft", help="DSC 格式：ft、f、f2 或 f2pvsc；默认 ft。")
    parser.add_argument("--include-pv-id", type=int, action="append", help="可选：仅生成指定逻辑 PVID；可重复指定。")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出每首 PV 的 JSON/SRT 缓存目录。")
    parser.add_argument("--report", type=Path, required=True, help="输出批处理成功、跳过与失败明细 JSON 报告。")
    parser.add_argument("--extractor", type=Path, default=Path("scripts/extract_native_lyric_timeline.py"), help="单曲时间线提取脚本路径。")
    parser.add_argument("--verifier", type=Path, default=Path("scripts/verify_native_lyric_cache.py"), help="单曲缓存一致性校验脚本路径。")
    return parser.parse_args()


def discover_normal_dsc(extracted_rom: Path, script_dir: Path | None) -> list[tuple[int, Path]]:
    """在指定或默认的脚本目录发现 Normal DSC，按 PVID 排序去重。"""
    script_dir = script_dir or extracted_rom / "script"
    if not script_dir.is_dir():
        raise ValueError(f"未找到脚本目录：{script_dir}")
    discovered: dict[int, Path] = {}
    for path in script_dir.rglob("pv_*_normal.dsc"):
        match = PV_DSC_PATTERN.match(path.name)
        if match is not None:
            pv_id = int(match.group(1))
            if pv_id in discovered:
                raise ValueError(f"PVID {pv_id} 出现多个 Normal DSC：{discovered[pv_id]} 与 {path}")
            discovered[pv_id] = path
    if not discovered:
        raise ValueError("未在已提取目录中找到任何 pv_xxx_normal.dsc。")
    return sorted(discovered.items())


def load_script_mapping(script_map_dbs: list[Path] | None) -> dict[int, list[int]]:
    """读取一个或多个文本表的 Normal script_file_name，建立 DSC 编号到逻辑 PVID 的映射。"""
    if script_map_dbs is None:
        return {}
    pattern = re.compile(r"^pv_(\d+)\.difficulty\.normal\.0\.script_file_name=.*pv_(\d+)_normal\.dsc$")
    mapping: dict[int, list[int]] = {}
    for script_map_db in script_map_dbs:
        if not script_map_db.is_file():
            raise ValueError(f"脚本映射文本表不存在：{script_map_db}")
        for raw_line in script_map_db.read_text(encoding="utf-8").splitlines():
            match = pattern.match(raw_line)
            if match is None:
                continue
            logical_pv_id, dsc_pv_id = int(match.group(1)), int(match.group(2))
            logical_ids = mapping.setdefault(dsc_pv_id, [])
            if logical_pv_id not in logical_ids:
                logical_ids.append(logical_pv_id)
    if not mapping:
        raise ValueError("脚本映射文本表中未找到 Normal script_file_name 映射。")
    return mapping


def discover_mapped_normal_dsc(search_roots: list[Path], script_mapping: dict[int, list[int]]) -> tuple[list[tuple[int, Path]], list[int]]:
    """按文本表声明的脚本编号在多个资源根目录定位 DSC，并按 Steam/基础路径优先选择。"""
    matches: dict[int, list[Path]] = {}
    for root in search_roots:
        if not root.is_dir():
            raise ValueError(f"脚本搜索根目录不存在：{root}")
        for path in root.rglob("pv_*_normal.dsc"):
            match = PV_DSC_PATTERN.match(path.name)
            if match is not None and int(match.group(1)) in script_mapping:
                matches.setdefault(int(match.group(1)), []).append(path)
    result: list[tuple[int, Path]] = []
    missing: list[int] = []
    for dsc_pv_id in sorted(script_mapping):
        candidates = matches.get(dsc_pv_id, [])
        if not candidates:
            missing.append(dsc_pv_id)
            continue
        def priority(path: Path) -> tuple[int, str]:
            normalized = str(path).replace("\\", "/").lower()
            return (0 if "/rom_steam/rom/" in normalized else 1 if "/rom/script/" in normalized else 2, normalized)
        result.append((dsc_pv_id, sorted(candidates, key=priority)[0]))
    return result, missing


def run_checked(command: list[str]) -> str:
    """执行子脚本并在失败时保留中文可审计错误信息。"""
    result = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"子进程退出码为 {result.returncode}。")
    return output


def main() -> int:
    """按发现的 PVID 批量生成、校验缓存并写出结果报告。"""
    arguments = parse_arguments()
    try:
        script_mapping = load_script_mapping(arguments.script_map_db)
        if arguments.script_search_root:
            discovered, missing_dsc_ids = discover_mapped_normal_dsc(arguments.script_search_root, script_mapping)
        else:
            discovered = discover_normal_dsc(arguments.extracted_rom, arguments.script_dir)
            missing_dsc_ids = []
        candidates = [(logical_pv_id, dsc_pv_id, dsc_path) for dsc_pv_id, dsc_path in discovered for logical_pv_id in script_mapping.get(dsc_pv_id, [dsc_pv_id])]
        if arguments.include_pv_id:
            included_pv_ids = set(arguments.include_pv_id)
            candidates = [candidate for candidate in candidates if candidate[0] in included_pv_ids]
            if not candidates:
                raise ValueError("指定的逻辑 PVID 未在发现的 Normal DSC 中找到。")
        logical_ids = [pv_id for pv_id, _, _ in candidates]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("多个 Normal DSC 映射到同一逻辑 PVID。")
        if not all(path.is_file() for path in arguments.pv_db) or not arguments.opcode_db.is_file():
            raise ValueError("文本数据库或 opcode 数据库不存在。")
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        report = {"schema_version": 1, "source_rom": str(arguments.extracted_rom), "pv_db": [str(path) for path in arguments.pv_db], "success": [], "skipped": [], "failed": []}
        for dsc_pv_id in missing_dsc_ids:
            for logical_pv_id in script_mapping[dsc_pv_id]:
                report["failed"].append({"pv_id": logical_pv_id, "dsc_pv_id": dsc_pv_id, "dsc": None, "error": "文本表声明的 Normal DSC 未在搜索根目录中找到。"})
        for pv_id, dsc_pv_id, dsc_path in candidates:
            json_path = arguments.output_dir / f"PV{pv_id}.json"
            srt_path = arguments.output_dir / f"PV{pv_id}.native.srt"
            try:
                command = [sys.executable, str(arguments.extractor), "--pv-id", str(pv_id), "--dsc", str(dsc_path)]
                for pv_db_path in arguments.pv_db:
                    command.extend(["--pv-db", str(pv_db_path)])
                if arguments.allow_lyric_overrides:
                    command.append("--allow-lyric-overrides")
                command.extend(["--opcode-db", str(arguments.opcode_db), "--dsc-format", arguments.dsc_format, "--out-json", str(json_path), "--out-srt", str(srt_path)])
                run_checked(command)
                run_checked([sys.executable, str(arguments.verifier), "--timeline-json", str(json_path), "--srt", str(srt_path)])
                line_count = len(json.loads(json_path.read_text(encoding="utf-8"))["lines"])
                report["success"].append({"pv_id": pv_id, "dsc_pv_id": dsc_pv_id, "dsc": str(dsc_path), "lines": line_count, "json": str(json_path), "srt": str(srt_path)})
                print(f"完成：PV{pv_id:03d}，{line_count} 行。")
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
                details = str(error)
                entry = {"pv_id": pv_id, "dsc_pv_id": dsc_pv_id, "dsc": str(dsc_path), "reason": "无歌词事件", "details": details}
                if "DSC 中未读取到任何 LYRIC 事件。" in details:
                    report["skipped"].append(entry)
                    print(f"无需缓存：PV{pv_id:03d}，DSC 不含 LYRIC 事件。")
                else:
                    report["failed"].append({"pv_id": pv_id, "dsc_pv_id": dsc_pv_id, "dsc": str(dsc_path), "error": details})
                    print(f"跳过：PV{pv_id:03d}，{details}", file=sys.stderr)
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"批处理失败：{error}", file=sys.stderr)
        return 1
    print(f"批处理完成：成功 {len(report['success'])} 首，无歌词 {len(report['skipped'])} 首，失败 {len(report['failed'])} 首。报告：{arguments.report}")
    return 0 if not report["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
