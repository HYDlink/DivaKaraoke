#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""递归展开已解包 DIVA 资料树中的 FARC 文件，并写出可续跑报告。"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_arguments() -> argparse.Namespace:
    """解析既有 FarcPack、输入资料树、输出根目录与并行参数。"""
    parser = argparse.ArgumentParser(description="递归展开资料树中的 FARC 文件。")
    parser.add_argument("--farcpack", type=Path, required=True, help="现有 FarcPack.exe 路径。")
    parser.add_argument("--input-root", type=Path, required=True, help="已解包 CPK 的输入根目录。")
    parser.add_argument("--output-root", type=Path, required=True, help="FARC 展开结果根目录。")
    parser.add_argument("--report", type=Path, required=True, help="展开审计 JSON 报告输出路径。")
    parser.add_argument("--workers", type=int, default=1, help="并行 FarcPack 进程数，默认 1；FarcPack 默认按单进程安全执行。")
    parser.add_argument("--path-pattern", action="append", help="可重复指定的相对路径 glob，仅展开匹配 FARC。")
    parser.add_argument("--retry-failed", action="store_true", help="重试已有报告记录的失败项。")
    return parser.parse_args()


def output_directory(input_root: Path, output_root: Path, farc_path: Path) -> Path:
    """按输入相对路径为单个 FARC 生成无歧义的独立输出目录。"""
    relative = farc_path.relative_to(input_root)
    return output_root / relative.parent / relative.name


def is_complete_output(path: Path) -> bool:
    """仅将存在至少一个文件的输出目录视为已完成，支持安全断点续跑。"""
    return path.is_dir() and any(path.rglob("*"))


def extract_one(farcpack: Path, input_root: Path, output_root: Path, farc_path: Path) -> dict[str, object]:
    """调用既有 FarcPack 展开一个 FARC，并返回可写入报告的结果。"""
    destination = output_directory(input_root, output_root, farc_path)
    if is_complete_output(destination):
        return {"source": str(farc_path), "output": str(destination), "status": "skipped"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(farcpack), str(farc_path), str(Path(str(destination) + ".contents"))], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {"source": str(farc_path), "output": str(destination), "status": "failed", "error": (result.stdout + result.stderr).strip() or f"退出码 {result.returncode}"}
    file_count = sum(1 for path in destination.rglob("*") if path.is_file())
    if file_count == 0:
        return {"source": str(farc_path), "output": str(destination), "status": "failed", "error": "FarcPack 成功退出但未产生文件。"}
    return {"source": str(farc_path), "output": str(destination), "status": "success", "files": file_count}


def main() -> int:
    """发现所有 FARC、并行展开、汇总并写出可复用的审计报告。"""
    arguments = parse_arguments()
    try:
        if not arguments.farcpack.is_file() or not arguments.input_root.is_dir():
            raise ValueError("FarcPack.exe 或输入根目录不存在。")
        if arguments.workers < 1:
            raise ValueError("并行进程数必须大于零。")
        farcs = sorted(path for path in arguments.input_root.rglob("*.farc") if path.is_file())
        if arguments.path_pattern:
            farcs = [path for path in farcs if any(path.relative_to(arguments.input_root).match(pattern) for pattern in arguments.path_pattern)]
        if not farcs:
            raise ValueError("输入根目录中未找到 FARC 文件。")
        arguments.output_root.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, object]] = []
        with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
            futures = [executor.submit(extract_one, arguments.farcpack, arguments.input_root, arguments.output_root, path) for path in farcs]
            for index, future in enumerate(as_completed(futures), 1):
                entry = future.result()
                results.append(entry)
                if index % 100 == 0:
                    print(f"进度：{index}/{len(farcs)}，当前 {entry['status']}。")
        results.sort(key=lambda entry: str(entry["source"]))
        report = {"schema_version": 1, "input_root": str(arguments.input_root), "output_root": str(arguments.output_root), "success": [entry for entry in results if entry["status"] == "success"], "skipped": [entry for entry in results if entry["status"] == "skipped"], "failed": [entry for entry in results if entry["status"] == "failed"]}
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"FARC 展开失败：{error}", file=sys.stderr)
        return 1
    print(f"FARC 展开完成：成功 {len(report['success'])}，跳过 {len(report['skipped'])}，失败 {len(report['failed'])}。报告：{arguments.report}")
    return 0 if not report["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
