"""按当前DML配置只读审计默认及换唱音源，统计现有伴奏模式的结构性边界。"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import sys

from audit_non_vocal_audio import audit_audio, file_sha256
from export_lyrics import ChineseArgumentParser, discover_mods, official_roots

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "no_target_pair": "单/双声道：无独立可静音声道对",
    "empty_muted_pairs": "目标人声声道对全空：开关不改变声音",
    "empty_kept_pairs": "保留声道对全空：开启会失去全部音频",
    "duplicate_mix": "保留与静音轨为同一混音：不能独立去人声",
    "silent_file": "整首无音频信号",
    "nonstandard_channels": "非标准声道数量：需单独核查",
    "active_split_candidate": "两组均有有效信号：仅分轨候选，仍可能残留人声",
    "missing_audio": "引用音频未定位",
    "decode_failed": "解码失败",
}
HARD_LIMITS = {"no_target_pair", "empty_muted_pairs", "empty_kept_pairs", "duplicate_mix", "silent_file"}


# 按已有资源优先级查找相对文件，拒绝越出资源树的数据库路径。
def resolve_resource(relative, roots):
    path = Path(relative.replace("\\", "/").removeprefix("./"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"数据库包含不安全的资源路径：{relative}")
    return next((root / path for root in roots if (root / path).is_file()), None)


# 合并当前启用数据库及已有官方资源，保留每个音源字段的来源证据。
def discover_tracks(game, lyric_cache):
    mods, notes = discover_mods(game)
    officials = official_roots(argparse.Namespace(game_dir=game, extracted_root=None))
    roots = [Path(item["root"]) for item in mods]
    for root in reversed(officials):
        roots.extend(sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: ("steam" not in path.name, path.name)))
        roots.append(root)
    databases = list(dict.fromkeys(root / "rom" / name for root in roots for name in ("mod_pv_db.txt", "mdata_pv_db.txt", "pv_db.txt") if (root / "rom" / name).is_file()))
    fields, origins = {}, {}
    for database in databases:
        for line in database.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"^pv_(\d+)\.(.*?)=(.*)$", line)
            if match:
                key = (int(match[1]), match[2])
                fields.setdefault(key, match[3])
                origins.setdefault(key, str(database))
    cached_ids = {int(path.stem[2:]) for path in lyric_cache.glob("PV*.json") if re.fullmatch(r"PV\d+", path.stem)}
    script_paths = {}
    for (pv_id, key), value in fields.items():
        if re.fullmatch(r"difficulty\.[^.]+\.\d+\.script_file_name", key):
            actual = resolve_resource(value, roots)
            if actual:
                script_paths.setdefault(pv_id, []).append(str(actual))
    tracks = []
    for (pv_id, key), value in sorted(fields.items()):
        if key != "song_file_name" and not re.fullmatch(r"(?:another_song\.\d+\.song_file_name|ex_song\.\d+\.file)", key):
            continue
        if not value:
            continue
        variant = re.match(r"(another_song|ex_song)\.(\d+)\.", key)
        if variant:
            length = fields.get((pv_id, variant[1] + ".length"))
            if length is not None and int(variant[2]) >= int(length):
                continue
        path = resolve_resource(value, roots)
        prefix = key.rsplit(".", 1)[0] if variant else ""
        variant_name = fields.get((pv_id, prefix + ".vocal_disp_name")) or fields.get((pv_id, prefix + ".name")) if variant else "默认"
        # 同名换唱版本追加角色身份，防止只看曲名无法区分具体音源。
        character = (fields.get((pv_id, prefix + ".vocal_chara_num")) or fields.get((pv_id, prefix + ".chara"))) if variant else None
        if variant and character:
            variant_name = (variant_name or prefix) + f"（{character}）"
        tracks.append({
            "pv_id": pv_id,
            "title": fields.get((pv_id, "song_name"), "未知曲名"),
            "variant": variant_name or prefix,
            "vocal_character": character,
            "field": key,
            "relative_audio": value,
            "audio": str(path.resolve()) if path else None,
            "mapping_database": origins[(pv_id, key)],
            "in_lyric_cache": pv_id in cached_ids,
            "available_chart_reference_count": len(script_paths.get(pv_id, [])),
        })
    config_paths = [game / "config.toml"]
    for item in mods:
        # 原始Mod配置位于所属Mod根目录，include可能另指子目录。
        relative = Path(item["root"]).relative_to(game / "mods")
        config_paths.append(game / "mods" / relative.parts[0] / "config.toml")
    return tracks, {
        "game_dir": str(game),
        "resource_roots_high_to_low": [str(path) for path in roots],
        "databases_high_to_low": [{"path": str(path), "sha256": file_sha256(path)} for path in databases],
        "configuration_fingerprints": [{"path": str(path), "sha256": file_sha256(path)} for path in dict.fromkeys(config_paths) if path.is_file()],
        "lyric_cache": str(lyric_cache),
        "lyric_cache_pv_ids": sorted(cached_ids),
        "notes": notes,
    }


# 仅按信号存在性和重复关系判断结构性边界，不把非空声道当作已确认人声。
def classify_audio(audit):
    channels = audit["channels"]
    count = len(channels)
    if all(item["exact_silence"] for item in channels):
        return "silent_file"
    if count <= 2:
        return "no_target_pair"
    if count not in (4, 6, 8):
        return "nonstandard_channels"
    kept = [item for index, item in enumerate(channels) if (index // 2) % 2 == 0]
    muted = [item for index, item in enumerate(channels) if (index // 2) % 2 == 1]
    if all(item["exact_silence"] for item in muted):
        return "empty_muted_pairs"
    if all(item["exact_silence"] for item in kept):
        return "empty_kept_pairs"
    if audit["non_vocal_effect"]["positive_scaled_duplicate"]:
        return "duplicate_mix"
    return "active_split_candidate"


# 汇总默认、换唱及已有歌词曲库三个口径，避免重复物理文件扩大歌曲数量。
def summarize(tracks):
    groups = {
        "default_tracks": [item for item in tracks if item["field"] == "song_file_name"],
        "lyric_cache_default_tracks": [item for item in tracks if item["field"] == "song_file_name" and item["in_lyric_cache"]],
        "alternate_tracks": [item for item in tracks if item["field"] != "song_file_name"],
    }
    result = {}
    for name, items in groups.items():
        result[name] = {
            "count": len(items),
            "unique_audio_files": len({item["audio"] for item in items if item["audio"]}),
            "category_counts": dict(Counter(item["category"] for item in items)),
            "structural_limit_count": sum(item["category"] in HARD_LIMITS for item in items),
        }
    return result


# 输出中文可读清单，完整保留结构可用候选与尚未确认的音频边界。
def write_readable(output, report):
    lines = ["# 本机曲库伴奏模式声道结构审计", "", "本报告按当前启用数据库引用统计；默认音源按PVID计数，换唱版本另列。可定位谱面不等于已逐项确认选曲界面显示。", "", "非空人声位置只说明静音会改变信号，不能证明留下的伴奏无人声或和声。", ""]
    for scope, heading in (("lyric_cache_default_tracks", "已有歌词曲库默认音源"), ("default_tracks", "全部数据库默认音源"), ("alternate_tracks", "另选唱/角色换唱音源")):
        summary = report["summary"][scope]
        lines.extend([f"## {heading}", "", f"共{summary['count']}项，物理音频去重{summary['unique_audio_files']}份，结构性受限{summary['structural_limit_count']}项。", "", "| 类型 | 数量 |", "| --- | ---: |"])
        for category, count in summary["category_counts"].items():
            lines.append(f"| {LABELS[category]} | {count} |")
        lines.append("")
    lines.extend(["## 结构性受限默认歌曲", "", "| PVID | 曲名 | 原因 | 已有歌词缓存 |", "| --- | --- | --- | --- |"])
    for item in report["tracks"]:
        if item["field"] == "song_file_name" and item["category"] in HARD_LIMITS:
            lines.append(f"| PV{item['pv_id']:03d} | {item['title'].replace('|', '/')} | {LABELS[item['category']]} | {'是' if item['in_lyric_cache'] else '否'} |")
    lines.extend(["", "## 结构性受限换唱版本", "", "| PVID | 曲名 | 版本 | 原因 | 音源文件 |", "| --- | --- | --- | --- | --- |"])
    for item in report["tracks"]:
        if item["field"] != "song_file_name" and item["category"] in HARD_LIMITS:
            lines.append(f"| PV{item['pv_id']:03d} | {item['title'].replace('|', '/')} | {item['variant'].replace('|', '/')} | {LABELS[item['category']]} | {Path(item['audio']).name} |")
    lines.extend(["", "完整源文件哈希、逐声道统计及覆盖映射见同目录的library-audit.json与audio-audits.json。", ""])
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


# 解析参数，完整解码每份唯一音频，并保存可复查的中文清单和机器报告。
def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="按本机当前配置只读审计伴奏模式的声道结构边界", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助并退出")
    # 游戏目录参数：只读取DML配置和启用Mod资源，绝不部署。
    parser.add_argument("--game-dir", type=Path, required=True, help="本机游戏安装根目录，只读")
    # 输出目录参数：保存审计JSON、进度和中文清单，不写游戏目录。
    parser.add_argument("--output-dir", type=Path, required=True, help="审计报告输出目录")
    # 歌词缓存参数：限定用户已使用曲库的统计子集，不参与音频判定。
    parser.add_argument("--lyrics-cache", type=Path, default=ROOT / "artifacts/singer-full-export/cache", help="已有歌词缓存目录，用于单列该曲库数量")
    # 解码并发参数：限制同时运行的ffmpeg进程数量，默认三个。
    parser.add_argument("--workers", type=int, default=3, help="并发解码数量，范围1至4")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("并发解码数量必须为1至4")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        tracks, discovery = discover_tracks(args.game_dir, args.lyrics_cache)
        (args.output_dir / "discovery.json").write_text(json.dumps(discovery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unique = sorted({item["audio"] for item in tracks if item["audio"]})
        print(f"发现默认音源{sum(item['field']=='song_file_name' for item in tracks)}项，换唱音源{sum(item['field']!='song_file_name' for item in tracks)}项；去重后完整检查{len(unique)}份音频。", flush=True)
        audits, errors = {}, {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(audit_audio, Path(path)): path for path in unique}
            for done, future in enumerate(as_completed(pending), start=1):
                path = pending[future]
                try:
                    audits[path] = future.result()
                except Exception as error:
                    errors[path] = str(error)
                if done % 20 == 0 or done == len(unique):
                    print(f"整首音频审计进度：{done}/{len(unique)}；失败{len(errors)}。", flush=True)
                    (args.output_dir / "progress.json").write_text(json.dumps({"completed": done, "total": len(unique), "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
        for item in tracks:
            path = item["audio"]
            item["category"] = "missing_audio" if path is None else "decode_failed" if path in errors else classify_audio(audits[path])
            if path in audits:
                item["audio_sha256"] = audits[path]["sha256"]
            item["classification_label"] = LABELS[item["category"]]
        # 完整解码期间配置或数据库改变时，将本次结果明确标为快照不一致。
        changed_inputs = [item["path"] for item in discovery["configuration_fingerprints"] + discovery["databases_high_to_low"] if file_sha256(Path(item["path"])) != item["sha256"]]
        report = {"inputs_unchanged_during_audit": not changed_inputs, "changed_inputs": changed_inputs, "schema_version": 1, "scope": "当前启用数据库引用的默认及换唱资源；非空声道不证明实际音频声部分离", "summary": summarize(tracks), "tracks": tracks, "errors": errors, "discovery": discovery}
        (args.output_dir / "audio-audits.json").write_text(json.dumps({"files": [audits[path] for path in sorted(audits)]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output_dir / "library-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_readable(args.output_dir, report)
        print(f"曲库审计完成，结构性受限默认音源{report['summary']['default_tracks']['structural_limit_count']}项；结果已保存：{args.output_dir}", flush=True)
        if errors or changed_inputs or any(item["category"] == "missing_audio" for item in tracks):
            raise RuntimeError("部分音源未定位、解码失败或来源快照发生变化，详见审计报告")
    except Exception as error:
        parser.exit(1, f"曲库音频审计失败：{error}\n")


if __name__ == "__main__":
    main()
