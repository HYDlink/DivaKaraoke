# 歌词、注音与歌手工具

已有自己的 SRT 和旁路缓存时，直接按[安装说明](INSTALL.md)迁移即可。只有需要重新生成时才使用本页工具。

## 一次配置自己的目录

在项目或已安装 Mod 根目录创建 `.local` 目录，把 [config/local.example.toml](../config/local.example.toml) 复制为 `.local/environment.toml`，用文本编辑器填写其中的路径。

这个文件不会提交到 Git；你的 Agent 也应先读它。另一台电脑只需重新填写这个文件，不要改公共说明或脚本里的默认目录。相对路径以项目/Mod 根目录为基准。

| 字段 | 填什么 |
| --- | --- |
| `game_dir` | 你自己的游戏根目录，内有 `DivaMegaMix.exe` |
| `extracted_root` | 已提取官方资料的共同父目录 |
| `farcpack` | 已有 `FarcPack.exe` |
| `opcode_db` | 已有 Open-PD-Script-Editor 的 `opcode_db/db.json` |
| `output_dir` | 生成缓存和报告的位置，默认相对目录即可 |
| `install_dir` | 需要安装缓存的 Mod `lyrics` 目录；填入不会自动触发安装 |

`source_manifest` 是复杂曲包的可选来源清单，普通用户有完整 `extracted_root` 时可留空。`manual_singers_dir` 与 `janome_path` 通常可使用默认值。

## 生成前需要的资料

需要 Python 3.11+、Janome、已有 FarcPack 和匹配的 opcode 表。源码用户运行 `tools/setup_python_tools.cmd` 安装 Python 工具依赖；发行包附带运行库。

外部工具从各自上游取得，来源见[第三方声明](../THIRD_PARTY_NOTICES.md)。此入口只复用已有提取树，**不会自动提取整个游戏**，也不会在运行时解析 CPK。

官方提取根目录支持 `diva_main` / `main-extract`、`diva_main_region` / `main-region-extract` 及已拥有 DLC 的对应目录。提取树必须含已有文本表及 DSC 脚本，不能只把 CPK 所在目录填进去。复杂覆盖关系使用你自己的逐包来源清单；不要使用别人的设备路径清单。

## 日常操作

所有入口从自己的 `.local/environment.toml` 取路径：

| 操作 | 运行入口 | 是否安装到游戏 |
| --- | --- | --- |
| 生成歌词、注音和歌手缓存 | `tools/export_lyrics.cmd` | 否 |
| 安装上次成功生成的缓存 | `tools/install_lyrics.cmd` | 是 |
| 预览歌手标记与创建人工模板 | `tools/build_singer_colors.cmd` | 否 |
| 应用人工歌手修改并安装 | `tools/apply_singer_marks.cmd` | 是 |

先生成，再检查结果，最后显式安装。填好 `install_dir` 不会让普通导出自动写入游戏。安装前建议退出游戏并备份自己改过的歌词。

命令行预览也不会执行操作。以下多行写法用于 Git Bash，PowerShell/CMD 可合并为一行：

```bash
python scripts/run_local_tools.py export \
  --local-config .local/environment.toml \
  --dry-run
```

生成结果在 `output_dir/cache`：SRT 是歌词时间线，Ruby TSV 是注音，Singers TSV 是歌手标记。需要安装的文件受同一清单保护；文件被你修改过或哈希不匹配时，工具会拒绝覆盖，而不是直接破坏原文件。

## 读音与结果检查

自动读音不保证完全正确。先选一首熟悉的歌检查正文、读音和起止时间，再扩大使用；缺少可靠读音时可能保留空白。逐字音节对齐不属于本版功能。

更改字体不会修复错误读音，更换歌曲来源后也不要把旧歌手标记直接套到新文本上。
