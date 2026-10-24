#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线歌词短入口：发现有效来源，复用现有转换器，安全安装生成缓存。"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATTERN = re.compile(r"^pv_(\d+)\.difficulty\.normal\.0\.script_file_name=(.+)$")
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


class ChineseArgumentParser(argparse.ArgumentParser):
    """将标准参数解析器的标题和常见错误提示转为中文。"""

    def format_help(self) -> str:
        """将自动帮助的用途和选项标题转换为中文。"""
        return super().format_help().replace("usage: ", "用法：").replace("options:", "选项：")

    def format_usage(self) -> str:
        """将参数错误时的用法标题转换为中文。"""
        return super().format_usage().replace("usage: ", "用法：")

    def error(self, message: str) -> None:
        """以中文错误前缀呈现缺失、未知或无效参数。"""
        message = message.replace("the following arguments are required:", "缺少必需参数：").replace("unrecognized arguments:", "未知参数：").replace("expected one argument", "需要一个参数值")
        self.print_usage(sys.stderr)
        self.exit(2, f"参数错误：{message}\n")


def arguments() -> argparse.Namespace:
    """解析游戏输入、输出文件与显式安装参数。"""
    parser = ChineseArgumentParser(description="导出本机有效歌词缓存；默认只生成，不安装。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出。")
    parser.add_argument("--game-dir", type=Path, help="包含 DivaMegaMix.exe 和 DML 配置的游戏根目录。")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出缓存、来源清单与报告的目录。")
    parser.add_argument("--source-manifest", type=Path, help="高级来源清单；相对输入路径以清单目录为基准。")
    parser.add_argument("--extracted-root", type=Path, help="可选已提取官方 CPK 根目录；支持 diva_main 或 main-extract 等已有目录名。")
    parser.add_argument("--farcpack", type=Path, default=ROOT / "MikuMikuLibrary/FarcPack.exe", help="已有 FarcPack.exe 路径。")
    parser.add_argument("--opcode-db", type=Path, default=ROOT / "artifacts/Open-PD-Script-Editor/opcode_db/db.json", help="已有 Future Tone opcode 数据库路径。")
    parser.add_argument("--discover-only", action="store_true", help="仅生成来源发现报告，不解包或转换。")
    parser.add_argument("--install-dir", type=Path, help="显式安装输出缓存到 lyrics 目录；保护自定义 SRT 和 Ruby TSV。")
    parser.add_argument("--install-only", action="store_true", help="仅安装输出目录内上次成功生成的缓存。")
    parser.add_argument("--rebuild-ruby-only", action="store_true", help="复用上次成功的时间线与 SRT，仅批量补齐振假名，不重新提取或转换。")
    # 歌手补齐参数：仅复用成功缓存自动扫描多身份PV，并应用独立人工修订。
    parser.add_argument("--rebuild-singers-only", action="store_true", help="仅补齐全部多身份PV的歌手标记，不重新生成歌词或注音。")
    # 人工歌手修订目录参数：默认使用输出目录下manual-singers，文件不进入自动缓存替换。
    parser.add_argument("--manual-singers-dir", type=Path, help="可选人工歌手修订目录；默认输出目录/manual-singers。")
    parser.add_argument("--janome-path", type=Path, default=ROOT / "tools/furigana_runtime", help="已有 Janome 离线运行库路径。")
    result = parser.parse_args()
    if not result.install_only and not result.rebuild_ruby_only and not result.rebuild_singers_only and not result.game_dir and not result.source_manifest:
        parser.error("需要 --game-dir 或 --source-manifest。")
    if result.install_only and not result.install_dir:
        parser.error("--install-only 必须提供 --install-dir。")
    if sum((result.install_only, result.rebuild_ruby_only, result.rebuild_singers_only)) > 1:
        parser.error("安装、注音补齐、歌手补齐三个模式不可同时使用。")
    return result


def write_json(path: Path, document: object) -> None:
    """以 UTF-8 写入中文可读的审计 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def checksum(path: Path) -> str:
    """计算文件哈希，识别用户修改和可安全更新的生成缓存。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> None:
    """在项目目录执行既有工具，并保存原始诊断但仅输出中文状态。"""
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    if result.returncode:
        details = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise RuntimeError(f"既有转换工具失败（退出码 {result.returncode}）：{details[-2000:]}")


def inside(path: Path, root: Path) -> Path:
    """校验相对 Mod 路径不会越出其所属根目录。"""
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Mod 路径越出所属目录：{path}")
    return resolved


def discover_mods(game: Path) -> tuple[list[dict], list[dict]]:
    """按 DML 白名单、启用状态与 include 顺序发现有效资源目录。"""
    config_path = game / "config.toml"
    if not config_path.is_file():
        return [], [{"说明": "没有 DML 配置，仅使用官方数据。"}]
    config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    if not config.get("enabled", True):
        return [], [{"说明": "DML 已关闭，仅使用官方数据。"}]
    mods_path = game / config.get("mods", "mods")
    order = config.get("priority")
    if order is None:
        order = sorted(path.name for path in mods_path.iterdir() if path.is_dir()) if mods_path.is_dir() else []
    if not isinstance(order, list) or not all(isinstance(name, str) for name in order):
        raise ValueError("DML priority 必须为目录名字符串数组。")
    roots, notes = [], []
    for rank, name in enumerate(order):
        mod = inside(mods_path / name, mods_path)
        path = mod / "config.toml"
        if not path.is_file():
            notes.append({"模组": name, "说明": "没有配置，未纳入。"})
            continue
        settings = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        if not settings.get("enabled", True):
            notes.append({"模组": name, "说明": "已禁用，未纳入。"})
            continue
        includes = settings.get("include", [])
        if not isinstance(includes, list) or not all(isinstance(item, str) for item in includes):
            raise ValueError(f"模组 {name} 的 include 必须为字符串数组。")
        for index, include in enumerate(includes):
            root = inside(mod / include, mod)
            if not root.is_dir():
                notes.append({"模组": name, "目录": str(root), "说明": "include 目录缺失。"})
                continue
            # 只读直接映射的资源目录，不将 include=["."] 解释为启用所有嵌套曲包。
            roots.append({"name": name, "root": str(root), "rank": rank, "include_index": index})
    return roots, notes


def official_roots(args: argparse.Namespace) -> list[Path]:
    """优先复用本机既有清单中的官方解包树，绝不自动重复解包。"""
    known = {}
    manifest = ROOT / "artifacts/installed-native-lyric-sources.json"
    if manifest.is_file() and args.extracted_root is None:
        entries = json.loads(manifest.read_text(encoding="utf-8"))["sources"]
        for source in entries:
            if source["name"] == "官方基础包":
                known["diva_main"] = Path(source["extracted_rom"]).parent
                known["diva_main_region"] = Path(source.get("script_map_db", source["pv_db"])).parents[2]
            elif source["name"] == "官方 DLC00":
                known["diva_dlc00"] = Path(source["extracted_rom"]).parents[1]
                known["diva_dlc00_region"] = Path(source.get("script_map_db", source["pv_db"])).parents[2]
    aliases = {"diva_main": "main-extract", "diva_main_region": "main-region-extract", "diva_dlc00": "dlc00-extract", "diva_dlc00_region": "dlc00-region-extract"}
    result = []
    for stem in ("diva_main", "diva_main_region", "diva_dlc00", "diva_dlc00_region"):
        cpk = args.game_dir / f"{stem}.cpk"
        if not cpk.is_file():
            if stem.startswith("diva_dlc"):
                continue
            raise ValueError(f"缺少官方基础包：{cpk}")
        target = known.get(stem)
        if args.extracted_root:
            target = next((path for path in (args.extracted_root / stem, args.extracted_root / aliases[stem]) if path.is_dir()), None)
        if target is None or not target.is_dir():
            raise ValueError(f"{stem} 尚无可复用提取树。请提供 --extracted-root 或高级清单；短入口不会自动全量解包。")
        # 不把另一份游戏的本机历史树静默当作当前安装的来源。
        if args.extracted_root is None:
            default_game = Path("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus")
            if args.game_dir != default_game:
                raise ValueError("游戏路径与本机历史来源不同，请显式提供 --extracted-root 或高级来源清单。")
        stat = cpk.stat()
        print(f"命中既有提取：{stem} → {target}；来源大小 {stat.st_size} 字节，修改时间指纹 {stat.st_mtime_ns}。")
        result.append(target)
    return result


def auto_sources(args: argparse.Namespace, work: Path, mods: list[dict], notes: list[dict]) -> list[dict]:
    """合并有效文本表，并按资源优先级定位映射到逻辑 PVID 的歌词 DSC。"""
    official = official_roots(args)
    resource_roots = [Path(item["root"]) for item in mods]
    # 官方 Steam 专用目录先于公共目录；DLC 与主包目录仅用于相应的文本映射。
    for root in reversed(official):
        resource_roots.extend(sorted((path for path in root.iterdir() if path.is_dir()), key=lambda p: ("steam" not in p.name, p.name)))
        resource_roots.append(root)
    databases = []
    for root in resource_roots:
        for filename in ("mod_pv_db.txt", "mdata_pv_db.txt", "pv_db.txt"):
            path = root / "rom" / filename
            if path.is_file() and path not in databases:
                databases.append(path)
    if not databases:
        raise ValueError("没有发现官方或有效 Mod 的歌词文本表。")
    mapping = {}
    lyric_ids = set()
    for database in databases:
        for line in database.read_text(encoding="utf-8-sig").splitlines():
            lyric_match = re.match(r"^pv_(\d+)\.lyric\.\d+=", line)
            if lyric_match:
                lyric_ids.add(int(lyric_match[1]))
            match = DB_PATTERN.match(line)
            if match:
                pv_id, relative = int(match[1]), match[2].replace("\\", "/")
                # Charts 的 script_nc 不含原生歌词时序；保留下一有效歌曲来源。
                if "/script_nc/" in relative:
                    notes.append({"pv_id": pv_id, "来源": str(database), "说明": "Charts 谱面不作为歌词时序源，使用下一歌曲来源。"})
                    continue
                mapping.setdefault(pv_id, (relative, database))
    scripts = work / "effective" / "rom" / "script"
    scripts.mkdir(parents=True)
    selected = []
    missing = []
    for pv_id, (relative, database) in sorted(mapping.items()):
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError(f"PV{pv_id:03d} 包含不安全脚本路径。")
        candidates = [root / relative for root in resource_roots]
        source = next((path for path in candidates if path.is_file()), None)
        if source is None:
            missing.append({"pv_id": pv_id, "脚本": relative, "文本表": str(database)})
            continue
        if pv_id not in lyric_ids:
            from extract_native_lyric_timeline import load_opcode_lengths, read_lyric_events
            events, _ = read_lyric_events(source, load_opcode_lengths(args.opcode_db, "ft"), "ft")
            if any(lyric_id > 0 for _, lyric_id in events):
                raise ValueError(f"PV{pv_id:03d} 的脚本包含 LYRIC 但没有对应文本；可能为跨曲包物理编号冲突，请使用逐包高级清单。")
            notes.append({"pv_id": pv_id, "来源": str(database), "说明": "脚本无非零歌词事件且无歌词文本，不生成缓存。"})
            continue
        shutil.copy2(source, scripts / f"pv_{pv_id:03d}_normal.dsc")
        selected.append({"pv_id": pv_id, "dsc": str(source), "dsc_sha256": checksum(source), "mapping_db": str(database)})
    write_json(work / "effective-sources.json", {"selected": selected, "missing": missing, "databases": [{"path": str(path), "sha256": checksum(path)} for path in databases], "notes": notes})
    print(f"来源指纹完成：{len(selected)} 份 DSC、{len(databases)} 份文本表已记录 SHA-256；未重新解包。")
    if missing:
        raise ValueError(f"{len(missing)} 个有效歌曲映射缺少 DSC，详见 effective-sources.json；旧缓存保持不变。")
    return [{"name": "有效游戏歌曲", "extracted_rom": str(scripts.parent), "pv_dbs": [str(path) for path in databases], "allow_lyric_overrides": True}]


def manifest_sources(path: Path, work: Path) -> list[dict]:
    """转换高级清单输入路径，并将所有生成文件限定在本次暂存目录。"""
    from build_installed_native_lyric_caches import load_sources
    sources = load_sources(path)
    scalar_paths = ("extracted_rom", "script_dir", "script_map_db", "pv_db", "cpk", "extract_dir")
    list_paths = ("script_map_dbs", "pv_dbs", "script_search_roots")
    for index, original in enumerate(sources):
        source = dict(original)
        for key in scalar_paths:
            if key in source:
                source[key] = str((path.parent / source[key]).resolve())
        for key in list_paths:
            if key in source:
                source[key] = [str((path.parent / item).resolve()) for item in source[key]]
        if "extracted_rom" not in source:
            # MVP 的全部入口只接受已有提取树，禁止隐式全量解包。
            if source.get("reuse_extracted") is not True:
                raise ValueError(f"资料包 {source['name']} 必须设置 reuse_extracted=true；MVP 禁止新解包。")
            if not Path(source["extract_dir"]).is_dir():
                raise ValueError(f"资料包 {source['name']} 的既有提取目录不存在：{source['extract_dir']}；不会创建或解包。")
        source["output_dir"] = str(work / "sources" / str(index))
        source["report"] = str(work / "reports" / f"{index}.json")
        sources[index] = source
    return sources


def effective_known_sources(args: argparse.Namespace, work: Path, mods: list[dict], notes: list[dict]) -> list[dict] | None:
    """优先复用已验证逐包映射，并以当前启用目录筛选文本与排序来源。"""
    manifest = ROOT / "artifacts/installed-native-lyric-sources.json"
    default_game = Path("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus")
    if not manifest.is_file() or args.extracted_root or args.game_dir != default_game:
        return None
    sources = manifest_sources(manifest, work)
    officials, selected, known_names = [], [], set()
    list_keys = ("pv_dbs", "script_map_dbs")
    for source in sources:
        if source["name"].startswith("官方"):
            officials.append(source)
            continue
        extracted = Path(source["extracted_rom"])
        matched = [item for item in mods if extracted == Path(item["root"]) / "rom"]
        # script_1 等已验证补充来源仍属于 include=["."] 的直接 rom 树。
        if not matched:
            notes.append({"资料包": source["name"], "说明": "当前 include 或启用配置未选中，跳过。"})
            continue
        item = matched[0]
        known_names.add(item["name"])
        enabled_roots = [Path(root["root"]) for root in mods if root["name"] == item["name"]]
        for key in list_keys:
            if key in source:
                # 外部官方文本是受审计的补缺来源，Mod 数据库必须来自有效 include。
                source[key] = [path for path in source[key] if not Path(path).is_relative_to(args.game_dir / "mods") or any(Path(path).parent == root / "rom" for root in enabled_roots)]
        if "script_search_roots" in source:
            source["script_search_roots"] = [str(root) for root in enabled_roots]
        selected.append((item["rank"], item["include_index"], source))
    # 追加标准 rom/mod_pv_db + rom/script 新曲包，复杂布局保留显式清单入口。
    fallback_dbs = [str(source["pv_db"]) for source in officials if "pv_db" in source]
    overlays = []
    for item in mods:
        if item["name"] in known_names:
            continue
        root = Path(item["root"])
        database = root / "rom/mod_pv_db.txt"
        if not database.is_file():
            continue
        contents = database.read_text(encoding="utf-8-sig")
        if not re.search(r"^pv_\d+\.lyric\.\d+=", contents, re.MULTILINE):
            notes.append({"模组": item["name"], "说明": "没有独立歌词文本，作为谱面/封面来源不生成歌曲缓存。"})
            continue
        if not (root / "rom/script").is_dir():
            overlays.append((item["rank"], str(database)))
            notes.append({"模组": item["name"], "说明": "纯文本/翻唱覆盖，复用对应歌曲的既有 DSC 时间线。"})
            continue
        selected.append((item["rank"], item["include_index"], {"name": item["name"], "extracted_rom": str(root / "rom"), "script_map_db": str(database), "pv_dbs": [str(database), *fallback_dbs], "allow_lyric_overrides": True}))
    selected.sort(key=lambda entry: (-entry[0], -entry[1]))
    result = officials + [entry[2] for entry in selected]
    for source in result:
        rank = next((entry[0] for entry in selected if entry[2] is source), float("inf"))
        higher = [path for overlay_rank, path in overlays if overlay_rank < rank]
        if higher:
            databases = source.pop("pv_dbs", [source.pop("pv_db")] if "pv_db" in source else [])
            source["pv_dbs"] = list(dict.fromkeys([*higher, *databases]))
            source["allow_lyric_overrides"] = True
    for index, source in enumerate(result):
        source["output_dir"] = str(work / "sources" / str(index))
        source["report"] = str(work / "reports" / f"{index}.json")
        if "extracted_rom" in source and not Path(source["extracted_rom"]).is_dir():
            raise ValueError(f"既有提取源缺失：{source['extracted_rom']}；不会自动重新解包。")
        print(f"命中既有逐包映射：{source['name']} → {source.get('extracted_rom', source.get('extract_dir'))}。")
    fingerprints = []
    for source in result:
        paths = [source[key] for key in ("pv_db", "script_map_db") if key in source]
        paths.extend(path for key in list_keys for path in source.get(key, []))
        for path in dict.fromkeys(paths):
            fingerprints.append({"source": source["name"], "path": path, "sha256": checksum(Path(path))})
    print(f"命中既有来源，已计算 {len(fingerprints)} 份文本输入 SHA-256；DSC 哈希随导出清单记录。")
    write_json(work / "effective-sources.json", {"sources_low_to_high": result, "notes": notes, "template": str(manifest), "input_fingerprints": fingerprints})
    return result


def build(args: argparse.Namespace, sources: list[dict], work: Path) -> Path:
    """复用既有总控逐曲生成和校验，在完整成功后合并缓存并记录哈希。"""
    args.reuse_extracted = False
    merged = {}
    replacements = []
    for index, source in enumerate(sources):
        source.setdefault("output_dir", str(work / "sources" / str(index)))
        source.setdefault("report", str(work / "reports" / f"{index}.json"))
        print(f"正在生成并校验资料包：{source['name']}。")
        # 原总控子脚本使用项目相对路径，这里显式固定 cwd，不改变用户输入解析。
        command = [sys.executable, str(ROOT / "scripts/build_installed_native_lyric_caches.py"), "--source-manifest", str(work / "current-source.json"), "--farcpack", str(args.farcpack), "--opcode-db", str(args.opcode_db), "--lyrics-dir", str(work / "unused"), "--skip-deploy"]
        write_json(work / "current-source.json", {"schema_version": 1, "sources": [source]})
        run(command)
        report = json.loads(Path(source["report"]).read_text(encoding="utf-8"))
        for entry in report["success"]:
            pv_id = entry["pv_id"]
            if pv_id in merged:
                replacements.append({"pv_id": pv_id, "previous_source": merged[pv_id]["source_name"], "selected_source": source["name"]})
            merged[pv_id] = dict(entry, source_name=source["name"])
    publish = work / "publish"
    publish.mkdir()
    entries = []
    for pv_id, entry in sorted(merged.items()):
        srt = publish / f"PV{pv_id:03d}.srt"
        audit = publish / f"PV{pv_id:03d}.json"
        shutil.copy2(entry["srt"], srt)
        shutil.copy2(entry["json"], audit)
        entries.append({"pv_id": pv_id, "file": srt.name, "sha256": checksum(srt), "source_name": entry["source_name"], "dsc": entry["dsc"], "dsc_sha256": checksum(Path(entry["dsc"]))})
    write_json(publish / "export-manifest.json", {"schema_version": 1, "entries": entries, "replaced": replacements})
    generate_ruby_cache(publish, args.janome_path)
    generate_singer_cache(publish, args.manual_singers_dir)
    return publish


def generate_ruby_cache(publish: Path, janome_path: Path) -> None:
    """按最终胜出时间线生成逐行振假名及审计，将三件套纳入安装哈希清单。"""
    if not (janome_path / "janome").is_dir():
        raise ValueError(f"缺少 Janome 离线运行库：{janome_path}；不会发布缺注音的缓存。")
    sys.path.insert(0, str(janome_path))
    from janome.tokenizer import Tokenizer
    from generate_furigana_sidecar import generate_timeline_sidecar
    tokenizer = Tokenizer()
    document = json.loads((publish / "export-manifest.json").read_text(encoding="utf-8"))
    spans = 0
    reviewed = 0
    uncovered_rows = 0
    uncovered_characters = 0
    for entry in document["entries"]:
        pv_id = int(entry["pv_id"])
        prefix = f"PV{pv_id:03d}"
        timeline = json.loads((publish / f"{prefix}.json").read_text(encoding="utf-8"))
        srt = publish / f"{prefix}.srt"
        if checksum(srt) != entry["sha256"] or timeline.get("pv_id") != pv_id:
            raise ValueError(f"{prefix} 的 SRT 哈希或时间线编号不匹配；拒绝为不明文本生成注音。")
        # SRT 与时间线先用既有验证器核对，避免 Ruby 对上过时的文本或行序。
        run([sys.executable, str(ROOT / "scripts/verify_native_lyric_cache.py"), "--timeline-json", str(publish / f"{prefix}.json"), "--srt", str(srt)])
        try:
            tsv, audit = generate_timeline_sidecar(tokenizer, timeline)
        except (IndexError, TypeError, KeyError) as error:
            raise ValueError(f"{prefix} 的振假名生成失败，旧成功缓存保持不变：{error}") from error
        ruby = publish / f"{prefix}.ruby.tsv"
        ruby.write_text(tsv, encoding="utf-8")
        audit_path = publish / f"{prefix}.ruby.audit.json"
        write_json(audit_path, audit)
        spans += sum(len(row["spans"]) for row in audit["rows"])
        reviewed += sum(bool(row.get("review_reasons") or row.get("uncovered_kanji_positions")) for row in audit["rows"])
        uncovered_rows += sum(bool(row.get("uncovered_kanji_positions")) for row in audit["rows"])
        uncovered_characters += sum(len(row.get("uncovered_kanji_positions", [])) for row in audit["rows"])
        entry["files"] = [{"file": path.name, "sha256": checksum(path)} for path in (srt, ruby, audit_path)]
    document["schema_version"] = 2
    document["ruby_generation"] = {"songs": len(document["entries"]), "spans": spans, "rows_requiring_review": reviewed, "uncovered_kanji_rows": uncovered_rows, "uncovered_kanji_characters": uncovered_characters}
    write_json(publish / "export-manifest.json", document)
    print(f"振假名生成完成：{len(document['entries'])} 首、{spans} 个汉字词组；{reviewed} 行需复核，其中 {uncovered_rows} 行/{uncovered_characters} 个汉字未可靠标注，详见注音审计。")


def generate_singer_cache(publish: Path, manual_dir: Path) -> dict:
    """在最终胜出歌词上自动生成多身份歌手标记，将结果纳入统一成套安装清单。"""
    from build_singer_timeline import generate_cache_singers
    document = json.loads((publish / "export-manifest.json").read_text(encoding="utf-8"))
    for entry in document["entries"]:
        prefix = f"PV{int(entry['pv_id']):03d}"
        srt = publish / f"{prefix}.srt"
        if checksum(srt) != entry["sha256"]:
            raise ValueError(f"{prefix}歌词哈希已改变，拒绝生成错行歌手标记。")
        run([sys.executable, str(ROOT / "scripts/verify_native_lyric_cache.py"), "--timeline-json", str(publish / f"{prefix}.json"), "--srt", str(srt)])
    summary = generate_cache_singers(publish, publish, manual_dir=manual_dir)
    by_id = {record["pv_id"]: record for record in summary["records"]}
    for entry in document["entries"]:
        record = by_id[int(entry["pv_id"])]
        old_files = entry.get("files", [])
        entry["files"] = [item for item in old_files if ".singers." not in item["file"]]
        entry["singer"] = {key: record[key] for key in ("status", "identities", "reason", "unresolved_slots", "lines", "manual_lines", "unmapped_slots") if key in record}
        if record["status"] == "generated":
            entry["files"] += [{"file": name, "sha256": checksum(publish / name)} for name in record["files"]]
        else:
            for item in old_files:
                if re.fullmatch(r"PV\d+\.singers\.(?:tsv|audit\.json|md)", item["file"]):
                    path = publish / item["file"]
                    if path.exists():
                        path.unlink()
    document["schema_version"] = 3
    document["singer_generation"] = {key: summary[key] for key in ("scanned", "generated", "single_identity", "unresolved", "line_counts")}
    document["singer_generation"]["manual_dir"] = str(manual_dir.resolve())
    write_json(publish / "export-manifest.json", document)
    return summary


def manifest_files(document: dict, require_ruby: bool) -> list[dict]:
    """展开安装文件清单并校验文件名，兼容旧安装所有权而拒绝缺注音的新安装。"""
    result = []
    seen = set()
    for entry in document["entries"]:
        prefix = f"PV{int(entry['pv_id']):03d}"
        basic = {f"{prefix}.srt", f"{prefix}.ruby.tsv", f"{prefix}.ruby.audit.json"}
        singer_files = {prefix + suffix for suffix in (".singers.tsv", ".singers.audit.json", ".singers.md")}
        allowed = basic | singer_files
        files = entry.get("files", [{"file": entry["file"], "sha256": entry["sha256"]}])
        expected = basic | singer_files if entry.get("singer", {}).get("status") == "generated" else basic
        if require_ruby and {item["file"] for item in files} != expected:
            raise ValueError(f"{prefix} 缺少完整 SRT/振假名/歌手标记审计文件清单；请重新导出或使用 --rebuild-ruby-only。")
        for item in files:
            if item["file"] not in allowed or item["file"] in seen:
                raise ValueError("生成清单包含无效或重复文件名。")
            seen.add(item["file"])
            result.append(item)
    return result


def install(cache: Path, destination: Path) -> dict:
    """预检全部文件，仅覆盖哈希可确认归属的生成缓存，保留自定义 SRT/Ruby。"""
    document = json.loads((cache / "export-manifest.json").read_text(encoding="utf-8"))
    previous_path = destination / "export-install-manifest.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.is_file() else {"entries": []}
    files = manifest_files(document, require_ruby=True)
    owned = {item["file"]: item["sha256"] for item in manifest_files(previous, require_ruby=False)}
    # 迁移旧六曲MVP明确记录的旁路所有权；仅新歌手清单允许认领，用户修改仍受哈希保护。
    legacy_singers = destination.parent / "singer-mvp-manifest.json"
    if document.get("schema_version", 0) >= 3 and legacy_singers.is_file():
        for item in json.loads(legacy_singers.read_text(encoding="utf-8-sig"))["files"]:
            match = re.fullmatch(r"lyrics[\\/](PV\d+\.singers\.tsv)", item["relative"])
            if match and re.fullmatch(r"[0-9a-fA-F]{64}", item["sha256"]):
                owned.setdefault(match[1], item["sha256"].lower())
    tasks, conflicts = [], []
    for entry in files:
        filename = entry["file"]
        source, target = cache / filename, destination / filename
        if not source.is_file() or checksum(source) != entry["sha256"]:
            raise ValueError(f"生成缓存哈希不匹配：{filename}")
        if target.exists() and checksum(target) not in (owned.get(filename), entry["sha256"]):
            conflicts.append(filename)
        tasks.append((source, target))
    if conflicts:
        raise ValueError(f"安装已中止，以下自定义或修改过的歌词受到保护：{', '.join(conflicts)}。请备份并人工移开冲突文件后重试。")
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in tasks:
        temporary = target.with_name(target.name + ".export-tmp")
        shutil.copy2(source, temporary)
        temporary.replace(target)
    # 移除已禁用来源留下的旧生成缓存；修改过的文件仍保持用户所有权。
    current = {entry["file"] for entry in files}
    removed, retained = [], []
    for filename, digest in owned.items():
        if not re.fullmatch(r"PV\d+\.(?:srt|ruby\.tsv|ruby\.audit\.json|singers\.tsv|singers\.audit\.json|singers\.md)", filename) or filename in current:
            continue
        target = destination / filename
        if target.is_file() and checksum(target) == digest:
            target.unlink()
            removed.append(filename)
        elif target.exists():
            retained.append(filename)
    write_json(previous_path, document)
    print(f"安装完成：{len(document['entries'])} 首、{len(tasks)} 份歌词/注音/歌手文件；移除失效生成文件 {len(removed)} 份，保留用户修改 {len(retained)} 份。")
    return {"installed": len(document["entries"]), "files_installed": len(tasks), "removed": removed, "retained": retained}


def safe_output_path(path: Path, output_dir: Path) -> Path:
    """确认发布和递归清理目标在输出根目录内，并拒绝链接或 Windows 联接点。"""
    root = output_dir.resolve()
    absolute = path.absolute()
    if absolute == root or not absolute.is_relative_to(root):
        raise ValueError(f"缓存操作目标越出输出目录：{path}")
    current = absolute
    while current != root:
        if current.is_symlink():
            raise ValueError(f"缓存操作路径不允许符号链接：{current}")
        if current.exists():
            attributes = getattr(current.lstat(), "st_file_attributes", 0)
            if attributes & 0x400:
                raise ValueError(f"缓存操作路径不允许 Windows 联接点：{current}")
        current = current.parent
    resolved = absolute.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(f"缓存操作目标解析后越出输出目录：{path}")
    return resolved


def publish_snapshot(publish: Path, output_dir: Path) -> Path:
    """在已检查的输出目录内切换成功缓存快照，失败则恢复旧缓存。"""
    cache = safe_output_path(output_dir / "cache", output_dir)
    backup = safe_output_path(output_dir / "previous-cache", output_dir)
    publish = safe_output_path(publish, output_dir)
    if backup.exists():
        raise ValueError("存在 previous-cache 恢复目录，请人工核对恢复后再运行。")
    if cache.exists():
        safe_output_path(cache, output_dir).rename(safe_output_path(backup, output_dir))
    try:
        safe_output_path(publish, output_dir).rename(safe_output_path(cache, output_dir))
    except OSError:
        if backup.exists():
            safe_output_path(backup, output_dir).rename(safe_output_path(cache, output_dir))
        raise
    if backup.exists():
        shutil.rmtree(safe_output_path(backup, output_dir))
    return cache


def main() -> int:
    """先暂存并完整验证，再发布成功快照；失败不覆盖上一次成功缓存。"""
    args = arguments()
    for name in ("game_dir", "output_dir", "source_manifest", "extracted_root", "farcpack", "opcode_db", "install_dir", "janome_path", "manual_singers_dir"):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.resolve())
    if args.manual_singers_dir is None:
        args.manual_singers_dir = args.output_dir / "manual-singers"
    try:
        if args.install_only:
            install(args.output_dir / "cache", args.install_dir)
            return 0
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.rebuild_ruby_only or args.rebuild_singers_only:
            cache = safe_output_path(args.output_dir / "cache", args.output_dir)
            if not (cache / "export-manifest.json").is_file():
                raise ValueError("没有成功导出缓存，不能仅补齐注音。")
            work = Path(tempfile.mkdtemp(prefix="ruby-build-", dir=args.output_dir))
            publish = work / "publish"
            shutil.copytree(cache, publish)
            if args.rebuild_ruby_only:
                generate_ruby_cache(publish, args.janome_path)
            generate_singer_cache(publish, args.manual_singers_dir)
            cache = publish_snapshot(publish, args.output_dir)
            print(f"批量旁路补齐完成：{cache}；SRT 与原始时间线未重新提取。")
            if args.install_dir:
                install(cache, args.install_dir)
            return 0
        mods, notes = discover_mods(args.game_dir) if args.game_dir else ([], [])
        write_json(args.output_dir / "discovery.json", {"schema_version": 1, "mods_high_to_low": mods, "notes": notes, "advanced_manifest": str(args.source_manifest) if args.source_manifest else None})
        if args.discover_only:
            print(f"来源发现完成：{len(mods)} 个有效资源目录。报告：{args.output_dir / 'discovery.json'}")
            return 0
        if not args.farcpack.is_file() or not args.opcode_db.is_file():
            raise ValueError("缺少 FarcPack 或 opcode 数据库，请通过相应参数指定。")
        # 保留失败暂存树及报告用于诊断；成功快照只在完整生成后替换。
        work = Path(tempfile.mkdtemp(prefix="build-", dir=args.output_dir))
        if args.source_manifest:
            sources = manifest_sources(args.source_manifest, work)
        else:
            sources = effective_known_sources(args, work, mods, notes)
            if sources is None:
                sources = auto_sources(args, work, mods, notes)
        publish = build(args, sources, work)
        cache = publish_snapshot(publish, args.output_dir)
        write_json(args.output_dir / "latest-build.json", {"status": "生成校验成功", "work_dir": str(work), "sources": sources, "cache_dir": str(cache)})
        count = len(json.loads((cache / "export-manifest.json").read_text(encoding="utf-8"))["entries"])
        print(f"导出完成：{count} 首；缓存目录：{cache}。")
        if args.install_dir:
            install(cache, args.install_dir)
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, ImportError, json.JSONDecodeError) as error:
        print(f"歌词导出失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
