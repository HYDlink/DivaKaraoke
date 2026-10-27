#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查公共说明与打包清单，防止个人目录、历史流水和私有配置回到用户入口。"""
import re
from pathlib import Path
import subprocess
import sys

import package_public_release as package

ROOT = Path(__file__).resolve().parents[1]
USER_GUIDES = ("INSTALL.md", "OBS_CONNECTOR.md", "NON_VOCAL_SUPPORT.md", "SINGER_EXPORT_WORKFLOW.md",
               "LYRICS_EXPORT.md", "TROUBLESHOOTING.md")
LOCAL_PATH = re.compile(r"(?i)(?<![a-z0-9\\])[a-z]:[\\/]")


def verify_links(path: Path) -> None:
    """验证当前入口中的相对文件链接，不要求网络或历史归档可执行。"""
    for target in re.findall(r"\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        candidate = (path.parent / target.split("#", 1)[0]).resolve()
        if not candidate.exists():
            raise ValueError("当前文档相对链接不存在：" + path.name + " → " + target)


def readme_graph() -> set[Path]:
    """递归检查README可达的仓库说明和资源，不能只审计几个直接链接。"""
    pending = [ROOT / "README.md"]
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if LOCAL_PATH.search(text):
            raise ValueError("README可达页面包含设备路径：" + path.relative_to(ROOT).as_posix())
        for target in re.findall(r"\]\(([^\s)]+)\)", text):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            candidate = (path.parent / target.split("#", 1)[0]).resolve()
            if not candidate.is_relative_to(ROOT) or not candidate.exists():
                raise ValueError("README可达链接越界或不存在：" + target)
            if candidate.is_relative_to(ROOT / "docs/archive") or candidate.is_relative_to(ROOT / ".local"):
                raise ValueError("README可达入口重新导向历史流水或私有上下文：" + target)
            pending.append(candidate)
    return visited


def main() -> int:
    """检查文档、Git忽略边界与真实打包输入，拒绝私有内容注入。"""
    sys.stdout.reconfigure(encoding="utf-8")
    public = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in public:
        text = path.read_text(encoding="utf-8")
        if LOCAL_PATH.search(text):
            raise ValueError("公共文档仍有设备绝对路径：" + path.relative_to(ROOT).as_posix())
    for name in USER_GUIDES:
        path = ROOT / "docs" / name
        if re.search(r"本轮|本机唯一|本机已部署|部署凭据|验收流水|SHA-256：|##.*20\d\d-\d\d-\d\d", path.read_text(encoding="utf-8")):
            raise ValueError("用户指南混入开发流水：" + name)
        verify_links(path)
    reachable = readme_graph()
    for name, limit in (("STATUS.md", 60), ("PLAN.md", 60), ("CURRENT_HANDOFF.md", 40)):
        if len((ROOT / "docs" / name).read_text(encoding="utf-8").splitlines()) > limit:
            raise ValueError("当前状态文件又变成长期流水：" + name)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "[![" in readme or "BV1VTJe6NEqU" not in readme:
        raise ValueError("README图片与独立视频文字链接约定被破坏")
    if subprocess.run(["git", "check-ignore", "--quiet", ".local/environment.toml"], cwd=ROOT).returncode:
        raise ValueError("私有环境配置未被Git忽略")
    if subprocess.check_output(["git", "ls-files", ".local"], cwd=ROOT).strip():
        raise ValueError("本地私有目录已经被Git跟踪")
    files = package.gather(ROOT / "artifacts/build/x64/Release", ROOT / "assets")
    package.validate(files)
    for name, data in files.items():
        if name.startswith("docs/archive/") or ".local" in Path(name).parts or name in {"docs/STATUS.md", "docs/PLAN.md", "docs/CURRENT_HANDOFF.md"}:
            raise ValueError("玩家安装包重新收录了历史或私有上下文：" + name)
        if Path(name).suffix.lower() in {".md", ".py", ".cmd", ".toml", ".json"} and LOCAL_PATH.search(data.decode("utf-8", errors="replace")):
            raise ValueError("玩家安装包文本仍有设备绝对路径：" + name)
    for prohibited in (".local/environment.toml", "docs/archive/private-note.md", "docs/STATUS.md"):
        try:
            package.validate({**files, prohibited: b"test"})
        except ValueError:
            pass
        else:
            raise ValueError("打包器没有拒绝私有或历史输入")
    print(f"文档边界检查通过：README递归可达{len(reachable)}个站内文件、指南、短摘要、私有Git忽略及安装包白名单。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print("文档边界检查失败：" + str(error), file=sys.stderr)
        raise SystemExit(1)
