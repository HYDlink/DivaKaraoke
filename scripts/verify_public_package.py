#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在全新目录回读安装ZIP、验证工具运行库及Windows DLL装载。"""
from __future__ import annotations

import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from export_lyrics import ChineseArgumentParser
from audit_release_privacy import findings


def run(command: list[str], title: str) -> None:
    """捕获子进程输出，只用中文摘要表示通过或失败。"""
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise ValueError(title + "失败，退出码：" + str(result.returncode))
    print(title + "通过。")


def run_script(script: Path, arguments: list[str], title: str) -> None:
    """在隔离解释器中只加入安装包自身脚本目录，避免借用工作区模块。"""
    code = ("import runpy,sys; sys.path.insert(0," + repr(str(script.parent)) + "); sys.argv="
            + repr([str(script), *arguments]) + "; runpy.run_path(" + repr(str(script)) + ",run_name='__main__')")
    run([sys.executable, "-I", "-c", code], title)


def main() -> int:
    """从明确ZIP路径建立新的安装检查目录，不覆盖用户已有安装。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="独立检查DivaKaraoke公开安装ZIP。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助。")
    # 安装包输入参数：只读取已有公开ZIP，不读取任何私有恢复包。
    parser.add_argument("--zip", type=Path, required=True, help="公开安装ZIP路径。")
    # 输出结果目录参数：必须是尚不存在的新目录，保存解压文件和脱敏验证JSON。
    parser.add_argument("--output-dir", type=Path, required=True, help="全新干净安装检查目录。")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("输出目录已存在，请使用新的检查目录，避免覆盖。")
    hits = []
    with zipfile.ZipFile(args.zip) as archive:
        manifest = json.loads(archive.read("DivaKaraoke/release-manifest.json"))
        expected = {"DivaKaraoke/" + item["路径"]: item for item in manifest["文件"]}
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("安装ZIP出现重复条目。")
        if set(archive.namelist()) != set(expected) | {"DivaKaraoke/release-manifest.json"}:
            raise ValueError("安装ZIP条目不符合发布清单。")
        for name in archive.namelist():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or ".local" in relative.parts or name.startswith("DivaKaraoke/docs/archive/") or not name.startswith("DivaKaraoke/"):
                raise ValueError("安装ZIP包含越界路径。")
            data = archive.read(name)
            if name in expected and (len(data) != expected[name]["字节"] or hashlib.sha256(data).hexdigest() != expected[name]["SHA256"]):
                raise ValueError("安装ZIP文件哈希不符：" + name)
            for hit in findings(data):
                hits.append({"文件": name, **hit})
        if hits:
            # 任何命中只报告位置，绝不回显可能的原文。
            raise ValueError("安装ZIP疑似认证信息命中：" + json.dumps(hits, ensure_ascii=False))
        archive.extractall(args.output_dir)
    root = args.output_dir.resolve() / "DivaKaraoke"
    if (root / "tools/obs-helper.json").exists():
        raise ValueError("安装ZIP不应携带私人OBS配置。")
    for name in ("export_lyrics.py", "run_local_tools.py"):
        script = root / "scripts" / name
        run_script(script, ["--help"], "安装目录工具中文帮助：" + name)
    run([sys.executable, "-I", str(root / "tools/obs_helper.py"), "--help"], "安装目录OBS助手启动帮助")
    for directory, module in (("furigana_runtime", "janome"), ("obs_runtime", "websocket")):
        runtime = root / "tools" / directory
        code = "import sys,pathlib; root=pathlib.Path(" + repr(str(runtime)) + "); sys.path.insert(0,str(root)); import " + module + "; assert pathlib.Path(" + module + ".__file__).resolve().is_relative_to(root)"
        run([sys.executable, "-I", "-c", code], "独立随包运行库：" + module)
    # 用空的隔离游戏目录执行只发现模式，验证新电脑无需维护者目录且不会自动安装。
    private = root / ".local"
    private.mkdir()
    fake_game = private / "空白游戏夹具"
    fake_game.mkdir()
    target = private / "不得自动创建的安装目标"
    template = (root / "config/local.example.toml").read_text(encoding="utf-8")
    template = template.replace('game_dir = ""', 'game_dir = ' + json.dumps(str(fake_game), ensure_ascii=False))
    template = template.replace('install_dir = ""', 'install_dir = ' + json.dumps(str(target), ensure_ascii=False))
    config = private / "environment.toml"
    config.write_text(template, encoding="utf-8")
    run_script(root / "scripts/run_local_tools.py", ["export", "--local-config", str(config), "--dry-run"], "安装目录私有配置预览")
    run_script(root / "scripts/export_lyrics.py", ["--local-config", str(config), "--discover-only"], "安装目录私有配置与来源发现")
    if target.exists() or not (root / "artifacts/exported-lyrics/discovery.json").is_file():
        raise ValueError("安装包的本地配置输出或显式安装边界不正确。")
    modules = [Path(item["路径"]).stem for item in manifest["文件"] if item["路径"].startswith("scripts/") and item["路径"].endswith(".py")]
    code = "import importlib,sys; sys.path.insert(0," + repr(str(root / "scripts")) + "); [importlib.import_module(name) for name in " + repr(modules) + "]"
    run([sys.executable, "-I", "-c", code], "安装包日常脚本依赖完整性")
    dll = root / "DivaKaraoke.dll"
    loaded = ctypes.WinDLL(str(dll))
    for name in ("D3DInit", "Init", "OnFrame"):
        getattr(loaded, name)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.FreeLibrary.argtypes = [ctypes.c_void_p]
    if not kernel.FreeLibrary(loaded._handle):
        raise ValueError("DLL独立释放失败。")
    with args.zip.open("rb") as source:
        archive_hash = hashlib.file_digest(source, "sha256").hexdigest()
    report = {"状态": "干净解压、哈希与脱敏、随包依赖、私有配置、无自动安装及DLL装载通过",
              "源码提交": manifest["源码提交"], "ZIP_SHA256": archive_hash, "安装文件数": len(expected) + 1,
              "DLL_SHA256": hashlib.sha256(dll.read_bytes()).hexdigest(), "游戏内验证": "IN-GAME VERIFICATION REQUIRED",
              "限制": "验证使用本机Windows与已安装VC++运行库；未执行游戏Hook、未连接OBS，也不冒充另一台物理电脑实测。"}
    (args.output_dir / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("公开安装ZIP干净目录验证通过，结果已保存。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print("安装包检查失败：" + str(error), file=sys.stderr)
        raise SystemExit(1)
