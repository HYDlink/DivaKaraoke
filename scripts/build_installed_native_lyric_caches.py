#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按资料包清单解包、构建、校验并部署 DIVA 原生歌词缓存。"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_arguments() -> argparse.Namespace:
    """解析资料包清单、既有工具与运行时歌词目录参数。"""
    parser = argparse.ArgumentParser(description="按清单批量构建并部署 DIVA 原生歌词缓存。")
    parser.add_argument("--source-manifest", type=Path, required=True, help="资料包 JSON 清单。")
    parser.add_argument("--farcpack", type=Path, required=True, help="现有 FarcPack.exe 的路径。")
    parser.add_argument("--opcode-db", type=Path, required=True, help="Future Tone opcode 数据库。")
    parser.add_argument("--lyrics-dir", type=Path, required=True, help="MMFreeLyrics 的运行时 lyrics 目录。")
    parser.add_argument("--reuse-extracted", action="store_true", help="所有解包目录已存在时跳过 FarcPack。")
    parser.add_argument("--skip-deploy", action="store_true", help="只生成和校验缓存报告，不写入运行时目录。")
    parser.add_argument("--duplicate-policy", choices=("error", "replace"), default="replace", help="重复 PVID 的部署策略；默认按清单顺序以后者覆盖前者。")
    return parser.parse_args()


def load_sources(manifest_path: Path) -> list[dict[str, object]]:
    """读取并验证资料包清单，拒绝不完整或重名资料包。"""
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("sources"), list):
        raise ValueError("资料包清单必须包含 schema_version=1 与 sources 数组。")
    sources: list[dict[str, object]] = []
    names: set[str] = set()
    required = {"name", "output_dir", "report"}
    for source in document["sources"]:
        if not isinstance(source, dict) or not required.issubset(source):
            raise ValueError("资料包清单项缺少必填字段。")
        if "extracted_rom" not in source and not {"cpk", "extract_dir", "rom_relative"}.issubset(source):
            raise ValueError(f"资料包 {source.get('name', '未知')} 必须提供 extracted_rom，或提供 CPK 解包字段。")
        if not isinstance(source["name"], str) or source["name"] in names:
            raise ValueError("资料包名称必须是唯一字符串。")
        has_external_databases = isinstance(source.get("pv_db"), str) or (isinstance(source.get("pv_dbs"), list) and all(isinstance(path, str) for path in source["pv_dbs"]))
        if not has_external_databases and not isinstance(source.get("pv_db_relative"), str):
            raise ValueError(f"资料包 {source['name']} 必须提供 pv_db、pv_dbs 或 pv_db_relative。")
        names.add(source["name"])
        sources.append(source)
    if not sources:
        raise ValueError("资料包清单为空。")
    return sources


def run_checked(command: list[str], title: str) -> None:
    """执行既有脚本，并将子进程异常转化为中文可审计错误。"""
    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError(f"{title}失败，退出码为 {result.returncode}。")


def ensure_complete_report(report_path: Path, source_name: str) -> None:
    """确认资料包所有候选 PV 成功，拒绝把半成品写入运行时。"""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failed = report.get("failed")
    if not isinstance(failed, list):
        raise ValueError(f"资料包 {source_name} 的报告格式无效。")
    if failed:
        ids = ", ".join(f"PV{int(item['pv_id']):03d}" for item in failed if isinstance(item, dict) and isinstance(item.get("pv_id"), int))
        raise ValueError(f"资料包 {source_name} 仍有未验证缓存：{ids or '未知 PVID'}。")


def build_source(arguments: argparse.Namespace, source: dict[str, object]) -> Path:
    """按资料包类型复用已解包构建器或 CPK 总控，并返回完整报告路径。"""
    if isinstance(source.get("extracted_rom"), str):
        command = [sys.executable, "scripts/build_native_lyric_caches.py", "--extracted-rom", str(source["extracted_rom"]), "--opcode-db", str(arguments.opcode_db), "--output-dir", str(source["output_dir"]), "--report", str(source["report"])]
        if isinstance(source.get("script_dir"), str):
            command.extend(["--script-dir", str(source["script_dir"])])
        if isinstance(source.get("script_search_roots"), list):
            for root in source["script_search_roots"]:
                command.extend(["--script-search-root", str(root)])
    else:
        command = [sys.executable, "scripts/extract_and_build_native_lyric_caches.py", "--farcpack", str(arguments.farcpack), "--cpk", str(source["cpk"]), "--extract-dir", str(source["extract_dir"]), "--rom-relative", str(source["rom_relative"]), "--opcode-db", str(arguments.opcode_db), "--output-dir", str(source["output_dir"]), "--report", str(source["report"])]
    if isinstance(source.get("script_relative"), str):
        command.extend(["--script-relative", str(source["script_relative"])])
    script_map_dbs = source.get("script_map_dbs") if isinstance(source.get("script_map_dbs"), list) else [source["script_map_db"]] if isinstance(source.get("script_map_db"), str) else []
    for script_map_db in script_map_dbs:
        command.extend(["--script-map-db", str(script_map_db)])
    if source.get("allow_lyric_overrides") is True:
        command.append("--allow-lyric-overrides")
    if isinstance(source.get("dsc_format"), str):
        command.extend(["--dsc-format", str(source["dsc_format"])])
    if isinstance(source.get("include_pv_ids"), list):
        for pv_id in source["include_pv_ids"]:
            command.extend(["--include-pv-id", str(pv_id)])
    if isinstance(source.get("pv_dbs"), list):
        for pv_db_path in source["pv_dbs"]:
            command.extend(["--pv-db", str(pv_db_path)])
    elif isinstance(source.get("pv_db"), str):
        command.extend(["--pv-db", str(source["pv_db"])])
    else:
        command.extend(["--pv-db-relative", str(source["pv_db_relative"])])
    if "extracted_rom" not in source and (arguments.reuse_extracted or source.get("reuse_extracted") is True):
        command.append("--reuse-extracted")
    run_checked(command, f"资料包 {source['name']} 缓存构建")
    report_path = Path(str(source["report"]))
    ensure_complete_report(report_path, str(source["name"]))
    return report_path


def main() -> int:
    """依清单完成所有资料包构建校验，并在全部通过后一次部署。"""
    arguments = parse_arguments()
    try:
        if not arguments.farcpack.is_file() or not arguments.opcode_db.is_file():
            raise ValueError("FarcPack.exe 或 opcode 数据库不存在。")
        reports = [build_source(arguments, source) for source in load_sources(arguments.source_manifest)]
        if not arguments.skip_deploy:
            command = [sys.executable, "scripts/deploy_native_lyric_caches.py", "--lyrics-dir", str(arguments.lyrics_dir), "--duplicate-policy", arguments.duplicate_policy]
            for report in reports:
                command.extend(["--report", str(report)])
            run_checked(command, "缓存部署")
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"总控流程失败：{error}", file=sys.stderr)
        return 1
    print(f"总控流程完成：已处理 {len(reports)} 个资料包。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
