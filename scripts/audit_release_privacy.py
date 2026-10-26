#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读扫描可发布文件及全部可达 Git 历史，报告不保存任何凭据原文。"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from export_lyrics import ChineseArgumentParser

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "GitHub令牌": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "OpenAI令牌": r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b",
    "云服务访问标识": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bAIza[A-Za-z0-9_-]{30,}\b",
    "Slack令牌": r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
    "私钥头": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    "带密码的网络地址": r"\b(?:https?|ssh|ftp)://[^\s/:@]+:[^\s/@]{3,}@",
}
ASSIGNMENT = re.compile(
    r'''(?i)["']?\b(password|passwd|pwd|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|obs[_-]?password)\b["']?\s*[:=]\s*["']([^"'\r\n]{1,512})["']'''
)
PLACEHOLDERS = {"password", "secret", "token", "example", "test", "changeme", "your_password", "your_token", "***", "xxx"}


def git(*args: str) -> bytes:
    """执行只读 Git 命令，失败时仅报告命令名称，避免回显认证地址。"""
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Git只读检查失败：{args[0]}")
    return result.stdout


def findings(data: bytes) -> list[dict]:
    """识别疑似凭据并仅返回行号、规则和长度，不返回原文或原文摘要。"""
    text = data.decode("utf-8", errors="replace")
    records = []
    for number, line in enumerate(text.splitlines(), 1):
        for name, pattern in RULES.items():
            if re.search(pattern, line):
                records.append({"行号": number, "类型": name})
        for match in ASSIGNMENT.finditer(line):
            value = match[2].strip()
            if value and value.lower() not in PLACEHOLDERS and not any(c in value for c in "{}<>$\\"):
                records.append({"行号": number, "类型": "非空认证字段（需人工区分示例）", "字段": match[1], "长度": len(value)})
    return records


def scan_history() -> dict:
    """逐个扫描所有本地引用可达的唯一文件对象，同时记录关联路径供定位。"""
    objects = {}
    for line in git("rev-list", "--objects", "--all").decode("utf-8", errors="replace").splitlines():
        oid, _, path = line.partition(" ")
        objects[oid] = path
    payload = ("\n".join(objects) + "\n").encode("ascii")
    checked = subprocess.run(["git", "cat-file", "--batch-check"], cwd=ROOT, input=payload, capture_output=True, check=True)
    blobs, metadata, skipped = [], [], []
    for line in checked.stdout.decode("ascii").splitlines():
        oid, kind, size = line.split()
        if kind in {"blob", "commit", "tag"}:
            if int(size) <= 8 * 1024 * 1024:
                blobs.append(oid)
                if kind != "blob":
                    metadata.append(oid)
            else:
                skipped.append({"对象": oid, "路径": objects[oid], "字节": int(size)})
    stream = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
                            input=("\n".join(blobs) + "\n").encode("ascii"), capture_output=True, check=True).stdout
    cursor, hits = 0, []
    for oid in blobs:
        end = stream.index(b"\n", cursor)
        size = int(stream[cursor:end].split()[2])
        data = stream[end + 1:end + 1 + size]
        cursor = end + size + 2
        for item in findings(data):
            hits.append({"对象": oid, "路径": objects[oid], **item})
    return {"扫描唯一文件对象数": len(blobs) - len(metadata), "扫描提交及标签对象数": len(metadata), "超限未扫描对象": skipped, "命中": hits}


def scan_private_archives(paths: list[str]) -> dict:
    """只在私有ZIP内存中检查配置，不解压，不把认证值写进报告。"""
    hits, count, skipped = [], 0, []
    for relative in paths:
        path = ROOT / relative
        if path.suffix != ".zip":
            skipped.append(relative)
            continue
        budget = 64 * 1024 * 1024
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                name = Path(entry.filename).name.lower()
                if not (name.endswith((".json", ".toml", ".ini", ".env")) or name in {"config", ".git-credentials", ".netrc"}):
                    continue
                if entry.file_size > 8 * 1024 * 1024 or entry.file_size > budget:
                    skipped.append(relative + "::" + entry.filename)
                    continue
                budget -= entry.file_size
                count += 1
                for item in findings(archive.read(entry)):
                    hits.append({"路径": relative + "::" + entry.filename, **item})
    return {"扫描配置条目数": count, "未扫描条目": skipped, "命中": hits}


def scan_local() -> dict:
    """扫描当前跟踪及未忽略文件，另查本机 Git 配置与被忽略的认证配置。"""
    paths = {ROOT / p.decode("utf-8") for p in git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if p}
    paths.add(ROOT / ".git/config")
    # 私有归档、模型及环境不递归读取；认证配置只记录脱敏命中。
    pruned = {".git", "node_modules", "venv", ".venv", "gpu-venv", "cpu-venv", "models", "separation-models", "site-packages", "__pycache__"}
    private_archives = []
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in pruned]
        for name in files:
            path = Path(directory) / name
            if name in {"obs-helper.json", ".netrc", "_netrc", ".git-credentials", "credentials", "id_rsa", "id_ed25519"} or name == ".env" or name.startswith(".env."):
                paths.add(path)
            if name.endswith((".zip", ".7z", ".bundle")) and "private" in name:
                private_archives.append(path.relative_to(ROOT).as_posix())
    hits, skipped, count = [], [], 0
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.stat().st_size > 8 * 1024 * 1024:
            skipped.append(relative)
            continue
        count += 1
        for item in findings(path.read_bytes()):
            hits.append({"路径": relative, **item})
    return {"扫描文件数": count, "超限未扫描文件": skipped, "私有归档": private_archives, "命中": hits}


def main() -> int:
    """读取报告输出参数，完成扫描并以中文输出脱敏统计。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="只读发布隐私检查；报告不含凭据原文。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助并退出。")
    # 输出文件参数：仅写入脱敏JSON，不复制扫描到的认证值。
    parser.add_argument("--output", type=Path, required=True, help="脱敏JSON报告输出路径。")
    args = parser.parse_args()
    report = {"说明": "仅为规则扫描，不保证识别全部秘密；未读取系统凭据管理器；私有ZIP仅在内存中检查配置条目。",
              "当前提交": git("rev-parse", "HEAD").decode().strip(), "历史": scan_history(), "本机": scan_local()}
    report["私有归档"] = scan_private_archives(report["本机"]["私有归档"])
    report["作者身份数量"] = len(set(git("log", "--all", "--format=%aN <%aE>").splitlines()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for section in ("历史", "本机", "私有归档"):
        print(f"{section}扫描完成：疑似命中{len(report[section]['命中'])}项。")
        for name, count in Counter(item["类型"] for item in report[section]["命中"]).items():
            print(f"  {name}：{count}项。")
    print(f"脱敏报告：{args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
