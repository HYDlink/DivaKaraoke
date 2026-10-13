# 本地版本记录与恢复

日期：2026-10-13。用户确认当前功能已足以录制展示，要求保存阶段性成果；MMFreeLyrics 上游许可仍待作者回复，本轮只保存本地版本，不公开发布。

## 当前里程碑

- 仓库根目录就是本项目工作目录，不需要重新初始化。
- 上游基线：86ca9825bba1e3c6a84a48d05768de4d57288c18。
- 本地分支：codex/recording-milestone-20261013。
- 本地标签：recording-ready-20261013。
- 用户确认当前实际录制展示可用；全曲注音人工复核、OBS 尾帧等历史未结项仍保留，不能将此里程碑理解为所有边界情况都已验证。

## 两层保存

| 位置 | 保存内容 | 用途 |
| --- | --- | --- |
| Git 提交 | Source、scripts、自有 tools、docs、testdata、配置示例、第三方声明和子模块固定版本 | 对比代码、继续开发和回到里程碑 |
| artifacts/local-snapshots/recording-ready-20261013 | 源码 Git bundle、安装版恢复包、离线工具与编译依赖、逐文件 SHA-256 清单 | 无网络恢复当前运行状态及源码依赖 |
| 原有 artifacts 和外部解包目录 | 历史构建、研究证据、完整游戏解包资料 | 保持原处，本轮不清理、不搬迁、不复制全部资料 |

ImGui 固定为 9aae45eb4a05a5a1f96be1ef37eb503a12ceb889，公开 SRT parser 固定为 38dd4def3eda841d1cb7cf6964a10fd8dbca22f7，toml11 固定为 1400dd223fb4297337266fcb5d04b700338aea71。子模块指针不会自动包含源文件，所以快照同时保存其实际源码；不依赖旧私有 parser。

MikuMikuLibrary 是第三方工具二进制目录，并不是另一个本地 Git 仓库。Janome 0.5.0 的词典较大，和 websocket-client 1.8.0 一并保存到工具恢复包，许可证随文件保留。Open-PD-Script-Editor 保存当前源码和 opcode 表，修订号记录在清单中。

## 恢复包说明

- source.bundle：主仓库全部本地引用及历史，包括里程碑分支和标签；不含子模块源码。
- installed-mod-private.zip：实际 DLL、当前 TOML、歌词、字体和配套工具，含本机 OBS 配置；跳过旧备份、日志、Git 元数据和解释器缓存。
- workspace-support.zip：MikuMikuLibrary、Python 离线运行库、opcode 工具和真实资料清单。
- build-dependencies.zip：当前编译依赖实际文件。
- 各包对应的 files.json：逐文件大小和 SHA-256。
- snapshot.json：源码提交、分支、安装 DLL 哈希、依赖修订及恢复包哈希。全部校验成功后才写出此完成标记，只有 ZIP 不能说明快照已完成。

安装 DLL 已核对哈希为 D14B37B870DAD217B2F626CA40E10AC3CE988C56587583E0AD6250DFE20B7832。本轮不重新构建、不替换游戏文件、不启动或停止游戏和 OBS。

这是本地私有记录。运行恢复包可能含 OBS 密码、字体、歌词及第三方文件，不应公开上传。上游来源和许可证声明保持原样，不给许可未解决的 MMFreeLyrics 添加自有许可证。origin 保留上游读取地址，并设置禁用的推送地址以避免误推。

恢复包没有保存完整游戏安装、F 盘资料树或全部约 10 GB 历史 artifacts。可恢复现有模组运行状态及开发文件；重新导出全部歌词仍需原有资料树或迁移后的来源清单。同盘快照不能替代异地备份，建议将整个目录复制到另一块备份盘。

## 日常保存与恢复

下一阶段按改动选择源码文件提交，不要强制添加 artifacts 绕过忽略规则。提交后，使用 PowerShell 7 在项目根目录运行：

```powershell
pwsh -NoProfile -File tools/save_local_snapshot.ps1 -SnapshotName local-20261014
```

工具禁止覆盖已有快照，要求工作区已提交，逐文件读取压缩包并校验 SHA-256，再验证 Git bundle。失败时保留文件供排查，换新名称重试；不会自动删除旧快照。

查看里程碑不会改变工作区：

```powershell
git log -1 recording-ready-20261013
git diff recording-ready-20261013 -- Source scripts tools docs
```

需要检查旧版时优先恢复到新目录，不直接重置当前工作区。以下命令是恢复示例，目标目录必须尚不存在：

```powershell
git clone -b codex/recording-milestone-20261013 artifacts/local-snapshots/recording-ready-20261013/source.bundle ../DivaKaraOkeLyrics-restored
Expand-Archive artifacts/local-snapshots/recording-ready-20261013/build-dependencies.zip ../DivaKaraOkeLyrics-restored
Expand-Archive artifacts/local-snapshots/recording-ready-20261013/workspace-support.zip ../DivaKaraOkeLyrics-restored
Expand-Archive artifacts/local-snapshots/recording-ready-20261013/installed-mod-private.zip ../MMFreeLyrics-restored
```

离线依赖恢复包不含子模块 .git 元数据，可以用于编译。需要继续管理子模块时，在网络和上游可用后按固定版本执行 git submodule update --init；纯文件恢复不代表子模块 Git 历史已恢复。新源码目录正常开发前应检查本机路径、依赖元数据和工具配置；游戏部署另按既有备份约定实施。
