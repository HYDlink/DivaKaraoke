#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复用 FarcPack 解包 CPK，并批量生成 DIVA 原生歌词缓存。"""

import argparse
import subprocess
import sys
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_arguments() -> argparse.Namespace:
    """解析 CPK 解包、文本表定位与缓存输出参数。"""
    parser = argparse.ArgumentParser(description="使用现有 FarcPack 解包 CPK 并批量生成歌词缓存。")
    parser.add_argument("--farcpack", type=Path, required=True, help="现有 FarcPack.exe 的路径。")
    parser.add_argument("--cpk", type=Path, required=True, help="待处理的官方或 Mod CPK 文件。")
    parser.add_argument("--extract-dir", type=Path, required=True, help="FarcPack 解包输出目录。")
    parser.add_argument("--rom-relative", type=Path, required=True, help="相对于解包目录且包含 script 子目录的目标 rom 路径。")
    parser.add_argument("--script-relative", type=Path, help="相对于目标 rom 的可选 DSC 目录；Charts Pack 使用 script_nc。")
    parser.add_argument("--script-map-db", type=Path, help="可选 mod_pv_db；按 Normal script_file_name 映射 DSC 与逻辑 PVID。")
    database_group = parser.add_mutually_exclusive_group(required=True)
    database_group.add_argument("--pv-db-relative", type=Path, help="相对于解包目录的 pv_db.txt 或 mdata_pv_db.txt 路径。")
    database_group.add_argument("--pv-db", type=Path, action="append", help="已提取且与 CPK 匹配的外部 pv_db、mdata_pv_db 或 mod_pv_db 路径；可重复指定。")
    parser.add_argument("--allow-lyric-overrides", action="store_true", help="多个文本表冲突时保留最先指定的文本，仅用后续表补缺失 ID。")
    parser.add_argument("--opcode-db", type=Path, required=True, help="Open-PD-Script-Editor 的 Future Tone opcode 数据库。")
    parser.add_argument("--dsc-format", choices=("ft", "f", "f2"), default="ft", help="DSC 格式：ft、f 或 f2；默认 ft。")
    parser.add_argument("--output-dir", type=Path, required=True, help="批量 JSON/SRT 缓存输出目录。")
    parser.add_argument("--report", type=Path, required=True, help="批处理 JSON 审计报告输出路径。")
    parser.add_argument("--builder", type=Path, default=Path("scripts/build_native_lyric_caches.py"), help="批量缓存生成脚本路径。")
    parser.add_argument("--reuse-extracted", action="store_true", help="解包目录已存在时不再次调用 FarcPack。")
    return parser.parse_args()


def find_rom_directory(extract_dir: Path) -> Path:
    """定位唯一包含 script 子目录的解包 rom 目录，拒绝歧义资料布局。"""
    candidates = [path for path in extract_dir.rglob("rom") if path.is_dir() and (path / "script").is_dir()]
    if len(candidates) != 1:
        raise ValueError(f"解包目录中应恰有一个含 script 的 rom 目录，实际为 {len(candidates)} 个。")
    return candidates[0]


def run_checked(command: list[str], title: str, accepted_codes: set[int] | None = None) -> None:
    """执行既有工具并将失败保留为中文错误，避免产生未验证缓存。"""
    result = subprocess.run(command)
    if result.returncode not in (accepted_codes or {0}):
        raise RuntimeError(f"{title}失败，退出码为 {result.returncode}。")


def main() -> int:
    """依次解包、定位资料、批量生成并校验每首歌词缓存。"""
    arguments = parse_arguments()
    try:
        if not arguments.farcpack.is_file() or not arguments.cpk.is_file():
            raise ValueError("FarcPack.exe 或 CPK 文件不存在。")
        if not arguments.reuse_extracted:
            arguments.extract_dir.mkdir(parents=True, exist_ok=True)
            run_checked([str(arguments.farcpack), str(arguments.cpk), str(arguments.extract_dir)], "FarcPack 解包")
        rom_dir = arguments.extract_dir / arguments.rom_relative
        script_dir = rom_dir / (arguments.script_relative or Path("script"))
        if not script_dir.is_dir():
            raise ValueError(f"未找到指定的 DSC 脚本目录：{script_dir}")
        pv_dbs = arguments.pv_db if arguments.pv_db is not None else [arguments.extract_dir / arguments.pv_db_relative]
        if not all(path.is_file() for path in pv_dbs):
            raise ValueError("未找到匹配的一个或多个文本表。")
        command = [sys.executable, str(arguments.builder), "--extracted-rom", str(rom_dir)]
        if arguments.script_relative is not None:
            command.extend(["--script-dir", str(rom_dir / arguments.script_relative)])
        if arguments.script_map_db is not None:
            command.extend(["--script-map-db", str(arguments.script_map_db)])
        for pv_db_path in pv_dbs:
            command.extend(["--pv-db", str(pv_db_path)])
        if arguments.allow_lyric_overrides:
            command.append("--allow-lyric-overrides")
        command.extend(["--opcode-db", str(arguments.opcode_db), "--dsc-format", arguments.dsc_format, "--output-dir", str(arguments.output_dir), "--report", str(arguments.report)])
        run_checked(command, "缓存批处理", {0, 2})
    except (OSError, RuntimeError, ValueError) as error:
        print(f"总控流程失败：{error}", file=sys.stderr)
        return 1
    print(f"总控流程完成：缓存目录 {arguments.output_dir}；报告 {arguments.report}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

