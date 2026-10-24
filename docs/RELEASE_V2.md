# 第二阶段里程碑：行级歌手归属与配色

日期：2026-10-25。用户认可当前阶段成果，要求先冻结、提交和打包，再进入第三版逐字时间开发。版本名称是本项目阶段号，不改写上游已有版本标签。

## 本阶段能力

- 从当前有效来源的角色表、复制槽和口型事件推测每一行的歌手归属。
- 支持单人/多人配色、合唱呈现、独立歌手配色保存和人工歌手修订。
- 自动导出既有309首歌词，62首多身份候选产生歌手旁路，安装时保护用户文件。
- 保留已交付的KTV、Ruby、伴奏和OBS功能，以及用户确认160FPS换句流畅的性能修复。

用户本次确认行级歌手归属作为第二阶段完成里程碑。这个阶段验收不把口型推测扩大为所有音频声部100%正确；剧情无声口型、缺口型、尚未解决的注音缺标及OBS结束尾帧等历史问题继续保留。第三版逐字时间功能尚未包含。

## 冻结与打包

- 源码分支：`codex/release-v2-singer-20261025`。
- 里程碑标签：`release-v2-singer-20261025`。
- 本地归档：`artifacts/local-snapshots/release-v2-singer-20261025/`。
- 正式完成凭据：`snapshot.json`和`release-v2.json`；仅ZIP存在不能代表校验完成。
- 已安装DLL SHA-256：`9FD8A1F547259A7A1A59D96BB2591FE8ED08927395A438C0A05A94DEFB8F05CB`，与最近已验证部署来源一致。

归档内容：Git bundle保留提交历史；安装包保存实际DLL/PDB、配置、字体、歌词、歌手标记和配套工具；工具/编译依赖独立打包；资源包保存当前时间线缓存、人工修订和全部明确引用的DSC/文本/操作码输入。完整游戏及F盘全量解包树保持原处，定位入口随资源包保存。

恢复范围和旧里程碑见[本地版本记录](LOCAL_VERSIONING.md)。本次包是本地私有恢复Release，包含私人配置与第三方资源，未授权或执行公开上传。

## 可重复的归档入口

先提交源码及标签，再运行PowerShell 7快照工具：

```powershell
pwsh -NoProfile -File tools/save_local_snapshot.ps1 -SnapshotName release-v2-singer-20261025
```

随后补齐资源包与发布清单；以下多行命令适用于Git Bash：

```bash
python scripts/package_stage2_release.py \
  --snapshot-dir artifacts/local-snapshots/release-v2-singer-20261025 \
  --cache-dir "E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/artifacts/exported-lyrics/cache"
```

工具禁止覆盖已有归档。每项回读SHA-256并核对源资料在打包期间没有变化；清单记录实际提交及安装DLL。第三版从该标签创建独立开发分支，恢复第二版时优先解压到新目录，不重置正在开发的工作区。
