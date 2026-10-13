#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将批量歌词缓存报告中的成功项部署到 MMFreeLyrics 运行时目录。"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# 固定脚本控制台输出为 UTF-8，避免 Windows 代码页导致中文日志乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_arguments() -> argparse.Namespace:
    """解析一个或多个缓存报告与运行时歌词目录参数。"""
    parser = argparse.ArgumentParser(description="部署批量歌词缓存报告中的成功 SRT 到 MMFreeLyrics。")
    parser.add_argument("--report", type=Path, action="append", required=True, help="批量缓存 JSON 报告路径；可重复提供。")
    parser.add_argument("--lyrics-dir", type=Path, required=True, help="MMFreeLyrics 的运行时 lyrics 目录。")
    parser.add_argument("--duplicate-policy", choices=("error", "replace"), default="error", help="重复 PVID 的处理方式；replace 按报告顺序以后者覆盖前者。")
    return parser.parse_args()


def load_success_entries(report_path: Path) -> list[dict[str, object]]:
    """读取报告成功项，并校验每项都有 PVID 与已生成 SRT 路径。"""
    document = json.loads(report_path.read_text(encoding="utf-8"))
    entries = document.get("success")
    if not isinstance(entries, list):
        raise ValueError(f"报告缺少 success 数组：{report_path}")
    result: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("pv_id"), int) or not isinstance(entry.get("srt"), str):
            raise ValueError(f"报告含无效成功项：{report_path}")
        if not Path(entry["srt"]).is_file():
            raise ValueError(f"缓存 SRT 不存在：{entry['srt']}")
        result.append(entry)
    return result


def main() -> int:
    """按运行时 PVxxx.srt 命名部署成功缓存，并写出可追溯清单。"""
    arguments = parse_arguments()
    try:
        entries = [entry for report in arguments.report for entry in load_success_entries(report)]
        by_pv_id: dict[int, dict[str, object]] = {}
        replaced: list[dict[str, object]] = []
        for entry in entries:
            pv_id = int(entry["pv_id"])
            if pv_id in by_pv_id:
                if arguments.duplicate_policy == "error":
                    raise ValueError(f"多个报告包含同一 PVID：PV{pv_id:03d}")
                replaced.append({"pv_id": pv_id, "previous_source": str(by_pv_id[pv_id]["srt"]), "selected_source": str(entry["srt"])})
            by_pv_id[pv_id] = entry
        arguments.lyrics_dir.mkdir(parents=True, exist_ok=True)
        deployed = []
        for pv_id, entry in sorted(by_pv_id.items()):
            source = Path(str(entry["srt"]))
            # 运行时始终按 PVxxx 三位编号查找；低编号也必须补零，不能沿用报告里的 PV37 命名。
            destination = arguments.lyrics_dir / f"PV{pv_id:03d}.srt"
            shutil.copy2(source, destination)
            deployed.append({"pv_id": pv_id, "source": str(source), "runtime_srt": str(destination)})
        manifest = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "deployed": deployed, "replaced": replaced}
        (arguments.lyrics_dir / "native-cache-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"部署失败：{error}", file=sys.stderr)
        return 1
    print(f"部署成功：{len(deployed)} 首缓存已写入 {arguments.lyrics_dir}；按优先级覆盖 {len(replaced)} 项。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
