#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在本地验证完成后同步指定独立仓库并发布安装包，不改写历史。"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from export_lyrics import ChineseArgumentParser

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "HYDlink/DivaKaraoke"
REMOTE = "https://github.com/" + REPOSITORY + ".git"
ENVIRONMENT = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")


def git(*args: str, accepted: tuple[int, ...] = (0,)) -> str:
    """捕获Git输出，失败不回显可能涉及认证的原始错误文本。"""
    result = subprocess.run(["git", *args], cwd=ROOT, env=ENVIRONMENT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode not in accepted:
        raise ValueError("Git操作未完成：" + args[0] + "；请检查登录、远端权限或分支冲突，未强制覆盖。")
    return result.stdout.strip()


def credential() -> str:
    """通过系统Git凭据管理器取得GitHub认证值，只在内存中使用。"""
    result = subprocess.run(["git", "credential", "fill"], cwd=ROOT, env=ENVIRONMENT,
                            input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True)
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    value = values.get("password")
    if result.returncode or not value:
        raise ValueError("GitHub尚未登录。请先用git credential-manager github login --username HYDlink --device完成网页授权；不需要把密码或Token写入项目。")
    return value


def api(token: str, method: str, url: str, value: dict | bytes | None = None, content_type: str = "application/json"):
    """只向GitHub指定仓库API发送认证请求，不输出请求头或认证值。"""
    allowed = ("https://api.github.com/repos/" + REPOSITORY, "https://uploads.github.com/repos/" + REPOSITORY + "/")
    if not any(url.startswith(prefix) for prefix in allowed):
        raise ValueError("拒绝向指定仓库以外的地址发送认证信息。")
    data = json.dumps(value, ensure_ascii=False).encode("utf-8") if isinstance(value, dict) else value
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "User-Agent": "DivaKaraoke-release", "Accept": "application/vnd.github+json",
        "Content-Type": content_type, "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404 and method == "GET":
            return None
        raise ValueError("GitHub API操作未完成，HTTP状态：" + str(error.code)) from None


def main() -> int:
    """先检查精确源码、安装包和干净验证凭据，显式发布时才修改远端。"""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ChineseArgumentParser(description="预检或发布清单对应版本的DivaKaraoke。默认只做本地预检。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示中文帮助。")
    # 发布目录参数：只上传已验证ZIP、校验值、文件清单和安装说明，不上传其它文件。
    parser.add_argument("--release-dir", type=Path, required=True, help="最终公开安装包、SHA256SUMS和验证凭据目录。")
    # 发布开关参数：用户显式选择后才推送main、标签并创建GitHub Release。
    parser.add_argument("--publish", action="store_true", help="实际同步指定GitHub仓库并发布。")
    args = parser.parse_args()
    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain"):
        raise ValueError("发布工作区有未提交文件，停止同步。")
    git("merge-base", "--is-ancestor", "ee5066b445117d1c28954140dd03ec1e1b5a41b5", "HEAD")
    if (ROOT / "Source/managers/character_timing.h").exists():
        raise ValueError("当前源码包含第三版逐字实现，不是用户选择的第二版。")
    directory = args.release_dir.resolve()
    manifest = json.loads((directory / "release-manifest.json").read_text(encoding="utf-8"))
    # 版本参数来自已验证清单，避免把维护版附件上传到旧标签。
    tag = "v" + manifest["版本"]
    verification = json.loads((directory / "package-verification.json").read_text(encoding="utf-8"))
    archive = directory / ("DivaKaraoke-" + tag + "-win64.zip")
    with archive.open("rb") as stream:
        archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    if manifest["源码提交"] != commit or verification["源码提交"] != commit or verification["ZIP_SHA256"] != archive_hash:
        raise ValueError("源码提交、安装包和干净目录验证凭据没有绑定。")
    checksum = (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").split()
    if checksum != [archive_hash, archive.name]:
        raise ValueError("公开SHA-256清单不匹配安装包。")
    print("发布本地预检通过：第二版源码、ZIP哈希与干净安装验证绑定。")
    if not args.publish:
        print("默认仅预检，没有联网、推送或发布。")
        return 0
    token = credential()
    base = "https://api.github.com/repos/" + REPOSITORY
    repository = api(token, "GET", base)
    if not repository or not repository.get("permissions", {}).get("push"):
        raise ValueError("当前GitHub账号没有目标仓库推送权限。")
    if "release" not in git("remote").splitlines():
        git("remote", "add", "release", REMOTE)
    elif git("remote", "get-url", "release") != REMOTE:
        raise ValueError("release远端地址不符合用户指定仓库。")
    git("push", "release", "HEAD:refs/heads/main")
    if git("tag", "--list", tag):
        if git("rev-parse", tag + "^{}") != commit:
            raise ValueError("本地版本标签已经指向其它提交，未改写标签。")
    else:
        git("tag", "-a", tag, "-m", "DivaKaraoke " + tag)
    git("push", "release", "refs/tags/" + tag)
    release = api(token, "GET", base + "/releases/tags/" + tag)
    if release is None:
        release = api(token, "POST", base + "/releases", {
            "tag_name": tag, "target_commitish": commit, "name": "DivaKaraoke " + tag,
            "body": (ROOT / "docs/RELEASE_NOTES.md").read_text(encoding="utf-8"), "draft": True, "prerelease": False})
    # 先在草稿中上传并核对摘要；重复执行不删除已有资产，也不覆盖不同内容。
    existing = {item["name"]: item for item in release.get("assets", [])}
    uploaded = []
    for path in (archive, directory / "SHA256SUMS.txt", directory / "release-manifest.json"):
        data = path.read_bytes()
        expected = "sha256:" + hashlib.sha256(data).hexdigest()
        item = existing.get(path.name)
        if item is None:
            url = release["upload_url"].split("{", 1)[0] + "?name=" + urllib.parse.quote(path.name)
            item = api(token, "POST", url, data, "application/zip" if path.suffix == ".zip" else "application/octet-stream")
        if item.get("digest") != expected or item.get("size") != len(data):
            raise ValueError("远端附件摘要未通过或已有同名不同内容附件；未删除或覆盖。")
        uploaded.append({"名称": path.name, "SHA256": expected[7:], "链接": item["browser_download_url"]})
    if release.get("draft"):
        release = api(token, "PATCH", base + "/releases/" + str(release["id"]), {"draft": False, "make_latest": "true"})
    # 草稿转公开后附件URL可能变化，重新读取元数据再保存公开链接。
    release = api(token, "GET", base + "/releases/" + str(release["id"]))
    final_assets = {item["name"]: item for item in release["assets"]}
    for item in uploaded:
        current = final_assets[item["名称"]]
        if current.get("digest") != "sha256:" + item["SHA256"]:
            raise ValueError("公开后附件摘要发生变化，停止确认发布结果。")
        item["链接"] = current["browser_download_url"]
    result = {"状态": "已同步并发布", "提交": commit, "标签": tag, "Release": release["html_url"], "附件": uploaded}
    (directory / "publication.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("源码、祖先历史与版本已发布：" + release["html_url"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print("发布未完成：" + str(error), file=sys.stderr)
        raise SystemExit(1)
