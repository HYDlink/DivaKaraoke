#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为已完成的本地源码/安装态快照补齐第二阶段资源与发布清单。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

from export_lyrics import ChineseArgumentParser

ROOT = Path(__file__).resolve().parents[1]
MOD = Path("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics")


def digest(path: Path) -> str:
    """流式计算文件SHA-256，避免把大资源一次加载进内存。"""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    """以UTF-8保存发布清单及校验结果。"""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verified_archive(destination: Path, sources: dict[str, Path]) -> dict:
    """保存不同磁盘的明确资源引用，逐项回读核对内容并检查源文件未变化。"""
    records = []
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative, source in sorted(sources.items()):
            expected = digest(source)
            archive.write(source, relative)
            records.append({"path": relative, "source": str(source.resolve()), "bytes": source.stat().st_size, "sha256": expected})
    with zipfile.ZipFile(destination) as archive:
        if len(archive.infolist()) != len(records):
            raise ValueError("资源包文件数不符。")
        for record in records:
            with archive.open(record["path"]) as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest().upper()
            if actual != record["sha256"] or digest(Path(record["source"])) != actual:
                raise ValueError(f"资源文件回读失败或源文件发生变化：{record['path']}")
    write_json(destination.with_suffix(".files.json"), records)
    return {"name": destination.name, "files": len(records), "bytes": destination.stat().st_size, "sha256": digest(destination)}


def package(snapshot: Path, cache: Path) -> dict:
    """从已校验恢复快照、安装缓存和源引用组成可追溯的第二阶段本地Release。"""
    summary = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8-sig"))
    for item in summary["archives"]:
        if digest(snapshot / item["name"]) != item["sha256"].upper():
            raise ValueError("已有恢复包哈希不符，停止归档。")
    if digest(snapshot / "source.bundle") != summary["source_bundle_sha256"].upper():
        raise ValueError("源码恢复包哈希不符。")
    inputs, resources, source_map = set(), {}, []
    timelines = sorted(path for path in cache.glob("PV*.json") if re.fullmatch(r"PV\d+\.json", path.name))
    for path in timelines:
        timeline = json.loads(path.read_text(encoding="utf-8"))
        inputs.add(Path(timeline["source"]["dsc"]).resolve())
        inputs.add(Path(timeline["source"]["opcode_db"]).resolve())
        inputs.update(Path(value).resolve() for value in timeline["source"]["pv_db"])
    for path in sorted(inputs):
        if not path.is_file():
            raise ValueError(f"离线重建源资料缺失：{path}")
        relative = f"inputs/{digest(path)[:16]}/{path.name}"
        resources[relative] = path
        source_map.append({"original": str(path), "archived": relative, "sha256": digest(path)})
    for directory in [cache, cache.parent / "manual-singers"]:
        if not directory.is_dir():
            raise ValueError(f"现有歌词资源目录缺失：{directory}")
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                resources[f"generated/{directory.name}/{path.relative_to(directory).as_posix()}"] = path
    # 资产入口只保存定位资料，完整原版游戏解包树保持原处；本包保存实际使用的DSC/文本输入。
    for relative in ["artifacts/installed-native-lyric-sources.json", "docs/EXTRACTED_ASSETS_INDEX.md", "docs/EXTRACTED_ASSET_REUSE.md"]:
        resources["references/" + Path(relative).name] = ROOT / relative
    mapping = snapshot / "resource-source-map.json"
    write_json(mapping, {"timeline_count": len(timelines), "inputs": source_map})
    resources["resource-source-map.json"] = mapping
    resource_archive = verified_archive(snapshot / "stage2-resources-private.zip", resources)
    installed = snapshot / "installed-mod-private.zip"
    with zipfile.ZipFile(installed) as archive:
        for required in ["MMFreeLyrics.dll", "MMFreeLyrics.pdb", "singer-colors.toml"]:
            if required not in archive.namelist():
                raise ValueError(f"安装恢复包遗漏必需文件：{required}")
        with archive.open("MMFreeLyrics.dll") as stream:
            dll_hash = hashlib.file_digest(stream, "sha256").hexdigest().upper()
        if dll_hash != summary["installed_dll_sha256"].upper():
            raise ValueError("发布DLL与安装态快照哈希不符。")
    release = {"schema_version": 1, "stage": 2, "name": "第二阶段：口型事件行级歌手归属与配色",
               "source_commit": summary["source_commit"], "source_branch": summary["source_branch"],
               "installed_dll_sha256": dll_hash, "timeline_count": len(timelines), "source_inputs": len(inputs),
               "archives": summary["archives"] + [resource_archive],
               "source_bundle_sha256": summary["source_bundle_sha256"],
               "verification": "源码历史与全部归档文件SHA-256回读通过；用户认可行级歌手功能为阶段里程碑",
               "known_limits": ["口型活动是行歌手归属证据，剧情无声/缺口型仍有例外", "注音缺标与OBS尾帧等既有待办保留", "第三版逐字功能尚未包含"],
               "privacy": "本地私有Release，包含用户配置及第三方资源，未上传。",
               "external_assets": "完整游戏安装及F盘全量解包树不复制；已保存当前歌词生成引用的全部DSC/文本/操作码表，运行字体和歌词在安装包中。"}
    write_json(snapshot / "release-v2.json", release)
    notes = ("# 第二阶段本地Release\n\n已冻结角色口型事件推测行级歌手归属、歌手配色与人工修订流程。\n\n"
             f"源码提交：{release['source_commit']}\n\n安装DLL SHA-256：{dll_hash}\n\n"
             f"已保存{len(timelines)}首时间线与{len(inputs)}份去重源输入。\n\n"
             "恢复时先验证release-v2.json内哈希，源码从source.bundle恢复；编译依赖、workspace-support、安装Mod和资源包分别解压到新目录。\n\n"
             "资源包的resource-source-map.json记录原路径和包内位置，迁移后须重新配置来源路径；勿直接覆盖正在运行的游戏。\n\n"
             "本地私有保存；归档校验不扩大既有实机验收范围。第三版从该里程碑另分支开发。\n")
    (snapshot / "第二阶段发布说明.md").write_text(notes, encoding="utf-8")
    return release


def main() -> int:
    """读取归档输入参数并执行资源打包，所有状态用中文输出。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="补齐第二阶段本地Release的资源恢复包。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出。")
    # 快照输入参数：必须已由本地快照工具完整校验，不覆盖已有资源包。
    parser.add_argument("--snapshot-dir", type=Path, required=True, help="已完成的本地恢复快照目录。")
    # 缓存输入参数：默认使用实际安装缓存，保存准确的运行资源与原始来源。
    parser.add_argument("--cache-dir", type=Path, default=MOD / "artifacts/exported-lyrics/cache", help="当前已安装的时间线和歌手缓存目录。")
    args = parser.parse_args()
    try:
        release = package(args.snapshot_dir, args.cache_dir)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"归档失败：{error}", file=sys.stderr)
        return 1
    print(f"第二阶段Release归档完成：{release['timeline_count']}首时间线，{release['source_inputs']}份源输入。")
    print(f"发布清单：{(args.snapshot_dir / 'release-v2.json').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
