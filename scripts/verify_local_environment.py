#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证设备配置、命令行优先级、来源隔离及显式安装边界，不操作真实游戏。"""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import export_lyrics as exporter
import local_environment as environment
import run_local_tools as runner


def require(value: bool, message: str) -> None:
    """用中文报告行为约束失败，不回显私有配置内容。"""
    if not value:
        raise ValueError(message)


def main() -> int:
    """在临时中文目录构造两份设备与两份游戏，只读测试路径选择。"""
    sys.stdout.reconfigure(encoding="utf-8")
    base = environment.ROOT / ".local/tests"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="设备配置 空格-", dir=base) as directory:
        root = Path(directory)
        game, other = root / "游戏甲", root / "游戏乙"
        for folder in (game, other):
            folder.mkdir()
            for name in ("diva_main.cpk", "diva_main_region.cpk"):
                (folder / name).touch()
        main_tree, region_tree = root / "主包", root / "文本包"
        (main_tree / "rom").mkdir(parents=True)
        database = region_tree / "rom_steam_region/rom/pv_db.txt"
        database.parent.mkdir(parents=True)
        database.write_text("", encoding="utf-8")
        manifest = root / "sources.json"
        manifest.write_text(json.dumps({"sources": [{"name": "官方基础包", "extracted_rom": str(main_tree / "rom"),
                                                   "pv_db": str(database), "script_map_db": str(database)}]}), encoding="utf-8")
        config = root / "environment.toml"
        config.write_text("[paths]\n" + "\n".join(name + " = " + json.dumps(str(value), ensure_ascii=False) for name, value in {
            "game_dir": game, "source_manifest": manifest, "output_dir": root / "输出", "install_dir": root / "安装目标"}.items()), encoding="utf-8")
        alternate = root / "另一配置.toml"
        alternate.write_text('[paths]\noutput_dir = "artifacts/relative-output"\n', encoding="utf-8")
        with patch.dict(os.environ, {"DIVA_KARAOKE_LOCAL_CONFIG": str(config)}):
            require(environment.load_environment()["game_dir"] == game, "未采用环境变量选择的本地配置")
            require(environment.load_environment(alternate)["output_dir"] == environment.ROOT / "artifacts/relative-output", "显式配置未优先或相对路径基准错误")
        with patch.object(sys, "argv", ["export_lyrics.py", "--local-config", str(config)]):
            args = exporter.arguments()
        require(args.game_dir == game and args.output_dir == root / "输出", "导出器未读取私有路径")
        require(args.install_dir is None, "普通导出因配置中存在安装目录而获得隐式安装权限")
        with patch.object(sys, "argv", ["export_lyrics.py", "--local-config", str(config), "--game-dir", str(other), "--output-dir", str(root / "显式输出")]):
            overridden = exporter.arguments()
        require(overridden.game_dir == other and overridden.output_dir == root / "显式输出", "命令行未覆盖本地配置")
        with redirect_stdout(io.StringIO()):
            require(exporter.official_roots(args) == [main_tree, region_tree], "未在绑定的设备游戏下复用已有提取树")
            try:
                exporter.official_roots(overridden)
            except ValueError:
                pass
            else:
                raise ValueError("把一份游戏的私有来源静默用于另一份游戏")
        values = environment.load_environment(config)
        command = runner.build_command("export", config, values)
        require("--install-dir" not in command and "--install-only" not in command, "普通导出命令包含安装参数")
        for action, flag in (("install", "--install-only"), ("apply", "--rebuild-singers-only")):
            command = runner.build_command(action, config, values)
            require(flag in command and "--install-dir" in command, "显式安装操作没有绑定安装目标")
        with patch.object(runner, "ROOT", root):
            try:
                runner.build_command("install", config, {})
            except ValueError:
                pass
            else:
                raise ValueError("源码目录在未配置目标时猜测了安装位置")
        require(not (root / "安装目标").exists(), "只读检查意外写入了安装目标")
        broken = root / "错误配置.toml"
        broken.write_text('[paths]\ntypo_dir = "test"\n', encoding="utf-8")
        try:
            environment.load_environment(broken)
        except ValueError:
            pass
        else:
            raise ValueError("未拒绝未知配置字段")
        with patch.object(sys, "argv", ["export_lyrics.py", "--local-config", str(broken), "--help"]), redirect_stdout(io.StringIO()):
            try:
                exporter.arguments()
            except SystemExit as result:
                require(result.code == 0, "错误配置阻断了中文帮助")
        require(environment.load_environment(root / "不存在.toml") == {}, "缺省文件不存在时行为错误")
        try:
            environment.load_environment(root / "不存在.toml", required=True)
        except ValueError:
            pass
        else:
            raise ValueError("显式配置缺失时未报错")
    print("本地配置回归通过：配置选择、中文路径、参数覆盖、来源隔离、帮助及显式安装保护。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print("本地配置验证失败：" + str(error), file=sys.stderr)
        raise SystemExit(1)
