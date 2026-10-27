#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取未提交的设备路径配置，供工具与开发助手共用。"""
from __future__ import annotations

import os
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PATH_KEYS = frozenset({"game_dir", "extracted_root", "farcpack", "opcode_db", "source_manifest",
                       "output_dir", "install_dir", "manual_singers_dir", "janome_path"})


def configuration_path(path: Path | str | None = None) -> Path:
    """选择显式文件、环境变量或仓库内默认文件，相对路径按项目根目录解释。"""
    selected = Path(path or os.environ.get("DIVA_KARAOKE_LOCAL_CONFIG") or ".local/environment.toml")
    return (selected if selected.is_absolute() else ROOT / selected).resolve()


def load_environment(path: Path | str | None = None, *, required: bool = False) -> dict[str, Path]:
    """读取有限的路径字段；不接受密码、令牌或可执行配置代码，也不写入游戏。"""
    selected = configuration_path(path)
    if not selected.is_file():
        if required:
            raise ValueError("本地环境配置不存在，请先复制并填写config/local.example.toml。")
        return {}
    try:
        document = tomllib.loads(selected.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError("本地环境配置无法读取或TOML格式错误。") from error
    if set(document) - {"paths"} or not isinstance(document.get("paths", {}), dict):
        raise ValueError("本地环境配置只接受[paths]表，私密认证应放在工具自己的私有配置中。")
    values = document.get("paths", {})
    if set(values) - PATH_KEYS:
        raise ValueError("本地环境配置包含不支持的字段，请对照示例检查。")
    result = {}
    for name, value in values.items():
        if not isinstance(value, str):
            raise ValueError("本地路径字段必须为字符串：" + name)
        if value.strip():
            candidate = Path(value)
            result[name] = (candidate if candidate.is_absolute() else ROOT / candidate).resolve()
    return result
