#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从明确白名单生成不含私人配置与游戏原始资料的公开安装ZIP。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import zipfile

from export_lyrics import ChineseArgumentParser
from audit_release_privacy import findings

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8-sig"))["version"]
USER_DOCUMENTS = (
    "README.md", "INSTALL.md", "OBS_CONNECTOR.md", "NON_VOCAL_SUPPORT.md",
    "SINGER_EXPORT_WORKFLOW.md", "LYRICS_EXPORT.md", "TROUBLESHOOTING.md", "BUILD.md",
    "ARCHITECTURE.md", "DECISIONS.md", "RELEASE_V020.md", "RELEASE_NOTES.md",
    "specs/README.md", "specs/lyrics.md", "specs/tools.md", "specs/documentation.md",
)
DAILY_SCRIPTS = (
    "export_lyrics.py", "local_environment.py", "run_local_tools.py",
    "build_installed_native_lyric_caches.py", "build_native_lyric_caches.py",
    "extract_and_build_native_lyric_caches.py", "extract_native_lyric_timeline.py",
    "verify_native_lyric_cache.py", "deploy_native_lyric_caches.py",
    "build_singer_timeline.py", "generate_furigana_sidecar.py", "furigana_alignment.py",
)


def digest(data: bytes) -> str:
    """计算打包实际字节的SHA-256，清单不记录本机输入绝对路径。"""
    return hashlib.sha256(data).hexdigest()


def gather(build: Path, assets: Path) -> dict[str, bytes]:
    """以固定文件清单收集公开包，不从游戏安装目录或私有恢复ZIP打包。"""
    files = {}
    for name in ("README.md", "LICENSING.md", "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md", "config.toml", "release-dependencies.json"):
        files[name] = (ROOT / name).read_bytes()
    files["DivaKaraoke.dll"] = (build / "DivaKaraoke.dll").read_bytes()
    lock = json.loads((ROOT / "release-dependencies.json").read_text(encoding="utf-8"))
    for item in lock["文件"]:
        if item["文件"].startswith("assets/fonts/"):
            font = assets / "fonts" / Path(item["文件"]).name
            data = font.read_bytes()
            if digest(data) != item["SHA256"]:
                raise ValueError("开放字体与锁定SHA-256不一致。")
            files["fonts/" + font.name] = data
    for path in sorted((ROOT / "LICENSES").glob("*.txt")):
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in USER_DOCUMENTS:
        files["docs/" + name] = (ROOT / "docs" / name).read_bytes()
    files["docs/assets/divakaraoke-preview.png"] = (ROOT / "docs/assets/divakaraoke-preview.png").read_bytes()
    for name in DAILY_SCRIPTS:
        files["scripts/" + name] = (ROOT / "scripts" / name).read_bytes()
    files["config/local.example.toml"] = (ROOT / "config/local.example.toml").read_bytes()
    # 保留使用入口；历史部署脚本与私有归档工具只留源码仓库，不放玩家安装目录。
    for name in ("obs_helper.py", "obs-helper.example.json", "obs-requirements.txt", "start_obs_helper.cmd", "start_obs_helper.bat",
                 "export_lyrics.cmd", "build_singer_colors.cmd", "apply_singer_marks.cmd", "install_lyrics.cmd", "setup_python_tools.cmd"):
        path = ROOT / "tools" / name
        if path.is_file():
            files["tools/" + name] = path.read_bytes()
    for directory in ("furigana_runtime", "obs_runtime"):
        base = ROOT / "tools" / directory
        if not base.is_dir():
            raise ValueError("缺少固定版本Python工具运行库，请运行tools/setup_python_tools.cmd。")
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"} and not any(part in {"tests", "test"} for part in path.relative_to(base).parts):
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in ("tools/furigana_runtime/Janome-0.5.0.dist-info/LICENSE.txt", "tools/furigana_runtime/Janome-0.5.0.dist-info/NOTICE.txt",
                 "tools/obs_runtime/websocket_client-1.8.0.dist-info/LICENSE"):
        if name not in files:
            raise ValueError("依赖许可证不完整，停止公开打包。")
    # 目录占位说明避免发布空目录丢失；实际歌词由用户迁移或从自己的游戏生成。
    files["lyrics/使用说明.txt"] = "将自己生成或已有的PV编号SRT、Ruby TSV、歌手TSV放到此处。v0.2.0不加载第三版逐字时间文件。详见docs/INSTALL.md。\n".encode("utf-8")
    files["安装说明.txt"] = "把DivaKaraoke整个文件夹放到游戏mods目录，停用旧MMFreeLyrics，在DML priority中启用DivaKaraoke。迁移自己的歌词缓存后可用双轨KTV；详细说明见docs/INSTALL.md。\n".encode("utf-8")
    return files


def validate(files: dict[str, bytes]) -> None:
    """拒绝私人配置和游戏原始资源，并只报告疑似凭据所在文件。"""
    config = tomllib.loads(files["config.toml"].decode("utf-8-sig"))
    if config.get("dll") != ["DivaKaraoke.dll"] or config.get("version") != VERSION:
        raise ValueError("Mod元数据版本或DLL名称不正确。")
    example = json.loads(files["tools/obs-helper.example.json"])
    if example.get("password"):
        raise ValueError("OBS示例配置包含非空密码。")
    for name, data in files.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.name in {"obs-helper.json", ".git-credentials", ".env"} or path.suffix.lower() in {".cpk", ".dsc", ".ogg", ".wav", ".mp4", ".pdb"}:
            raise ValueError("公开包包含禁用路径或资源：" + name)
        if ".local" in path.parts or name.startswith("docs/archive/") or name in {"docs/STATUS.md", "docs/PLAN.md", "docs/CURRENT_HANDOFF.md"}:
            raise ValueError("公开包包含本地上下文或开发流水：" + name)
        if path.suffix.lower() in {".json", ".toml", ".ini", ".env"} and findings(data):
            raise ValueError("公开包配置命中认证规则，请人工脱敏：" + name)


def main() -> int:
    """读取构建、开放资产与输出路径，生成可追溯且可回读校验的安装包。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="生成当前版本DivaKaraoke公开安装ZIP。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助。")
    # 构建输入参数：只接收本轮验证过的DivaKaraoke.dll，不读取游戏中的DLL。
    parser.add_argument("--build-dir", type=Path, default=ROOT / "artifacts/build/x64/Release", help="DLL构建输出目录。")
    # 开放资产输入参数：固定哈希的OFL字体目录，不允许复制用户商业字体目录。
    parser.add_argument("--assets-dir", type=Path, default=ROOT / "assets", help="已准备的开放字体资产目录。")
    # 输出结果文件参数：该目录保存ZIP、SHA256和逐文件清单，禁止覆盖已有同名发布。
    parser.add_argument("--output-dir", type=Path, required=True, help="公开ZIP及校验清单的输出目录。")
    args = parser.parse_args()
    files = gather(args.build_dir, args.assets_dir)
    validate(files)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"版本": VERSION, "源码提交": commit, "基线提交": "ee5066b445117d1c28954140dd03ec1e1b5a41b5",
                "文件": [{"路径": name, "字节": len(data), "SHA256": digest(data)} for name, data in sorted(files.items())],
                "说明": "公开包不含用户歌词缓存、私人配置、游戏原始资源及商业字体。装载与离线验证不等于游戏内验收。"}
    files["release-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / f"DivaKaraoke-v{VERSION}-win64.zip"
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo("DivaKaraoke/" + name, (2026, 10, 25, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or len(archive.infolist()) != len(files):
            raise ValueError("ZIP完整性检查失败。")
        for name, data in files.items():
            if archive.read("DivaKaraoke/" + name) != data:
                raise ValueError("ZIP回读与源文件不一致：" + name)
    with destination.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    (args.output_dir / "SHA256SUMS.txt").write_text(checksum + "  " + destination.name + "\n", encoding="utf-8")
    (args.output_dir / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"公开安装ZIP已生成并逐项回读通过：{len(files)}份文件。")
    print(f"安装包：{destination.resolve()}")
    print(f"SHA-256：{checksum}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print("公开打包失败：" + str(error), file=sys.stderr)
        raise SystemExit(1)
