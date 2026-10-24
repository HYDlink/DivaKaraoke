# 2026-10-15更新：自动多歌手与独立人工修订

默认歌词导出已集成全量多身份扫描，支持独立人工标记与快速重新应用。当前流程和命令以 [自动歌手导出工作流](SINGER_EXPORT_WORKFLOW.md) 为准；下方为早期阶段记录。

# 批量振假名修复（当前交付口径）

用户已要求暂停部署，当前只修工具和工作区产物，不写游戏目录。

导出默认在所有资料包合并完成后，按最终胜出的每首 SRT/时间线生成 PVxxx.ruby.tsv 和 PVxxx.ruby.audit.json；一次初始化已有 Janome，复用 generate_timeline_sidecar。旁路行号按最终 SRT 顺序，不使用原始 lyric_id，重复/跳号及清屏不造成错行。只有源文本与最终歌词一致才使用该源英文栏；未通过罗马音锚点检测的英文翻译不作为唱法，使用可确认词典读音并记录复核理由，未知词不造读音。

export-manifest schema_version=2 的每首 files 包括 SRT、Ruby TSV、Ruby 审计三件套哈希。安装一起预检和更新；自定义或修改过的 Ruby 与 SRT 受到相同保护，冲突时在正式写入前整体拒绝。哈希仍一致的失效生成旁路可回收，用户修订保留。旧版只有 SRT 的导出不能继续安装，必须补齐注音；旧安装清单仍可提供经过核对的 SRT 所有权。

只补齐已成功导出的全部注音，SRT 原文和时间线保持不变，不重新解包：

```bash
python scripts/export_lyrics.py \
  --output-dir artifacts/lyrics-ruby-mvp \
  --rebuild-ruby-only
```

这条命令要求 output-dir/cache 已有成功导出文件。默认完整导出也包含同一批量注音过程，不需要额外调用单曲生成器。输出和安装分离；本文多行命令的反斜杠展示遵循项目约定，PowerShell请合并成一行。

最终统计：309 首、11299 行、24313 个汉字词组注音；927 份 SRT/TSV/审计安装文件哈希全部正确，309 首 SRT 哈希保持不变。98 行需人工复核，其中44行/58个汉字未可靠标注，属于保留审计的局部特殊读音，不宣称100%覆盖。游戏现有 PV424 Ruby 与本次输出哈希均为 859ea08959d96f3f1f3ff8adc2d8118c4120623f0f90b75858d9f29e070d62fa，逐字节一致。

工作区交付为 artifacts/lyrics-ruby-mvp/cache；batch-ruby-verification.json 核对所有 SRT 哈希保持不变、每行和 Unicode 跨度对齐、安装文件哈希、PV424 字节一致。PV809 第17/44行声→こえ、震→ふる、伝→つた，第18/45行愛→あい、詩→うた、呼→よ、奇跡→きせき，均已真实样本确认。

不会宣称所有汉字读音100%准确。最终 manifest 的 ruby_generation 同时列出 rows_requiring_review、uncovered_kanji_rows、uncovered_kanji_characters，每首审计保留理由和未覆盖位置，供人工复核。

旧游戏 native-cache-manifest 不含哈希。只读迁移审计发现322份运行时 SRT 与其已审计原始生成来源哈希仍完全一致，可由主编排在部署获准后仅采用这些证明过的所有权，不能认领任意自定义文件。既有 PV424 Ruby 与新输出逐字节一致，可保留；legacy-install-migration-audit.json 记录证据，本轮没有写入或迁移游戏配置。

下面保留最初 MVP 的路径与命令说明；其“只保护而不生成 Ruby”描述由本节新的三件套流程替代。
# 歌词导出器 MVP

更新时间：2026-10-10。歌词功能已验收，本项只验证新工具，不重新要求 PV276/PV424 游戏验收。

双击 `tools/export_lyrics.cmd` 即可使用。默认读取本机 E 盘游戏配置和已有 `artifacts/installed-native-lyric-sources.json`，按 DML enabled、priority、Mod enabled/include 筛选来源，复用已有解包树。不会重新解包、不写游戏目录，输出在工作区 `artifacts/exported-lyrics/cache`。需要 Python 3.11+ 与已有 FarcPack/opcode 表。

复用既有提取/同源校验器，所有资料包通过才发布 cache；失败保留旧成功缓存和本次 build-* 诊断。SRT 是运行时格式，JSON 是审计文件，export-manifest.json 记录来源与 SRT/DSC 哈希，effective-sources.json 记录文本输入哈希。不会全量重新哈希数十 GB CPK，现有提取树的同源性依赖既有审计。

支持当前审计曲包、翻唱文本覆盖与标准 rom/mod_pv_db + rom/script 新曲包；复杂布局使用高级清单。高级清单仍按原有低到高顺序合并。本 MVP 所有入口均禁止新解包；高级 CPK 项必须设置 reuse_extracted=true 且 extract_dir 已存在，否则在调用工具或创建资产目录前以中文报错。EXE、智能增量和任意社区布局不是本 MVP 范围。

实际导出：309 首、9 份资料包报告零失败。第二次在不同 cwd 和中文空格输出路径执行；两次309首 SRT 哈希完全一致。逻辑验证覆盖有效 Mod 筛选、安装更新、失效缓存回收、用户 SRT/Ruby 保护、哈希篡改拒绝与冲突预检零写入。

历史322与当前309的13首差异：PV10003、PV10004、PV10006、PV10011、PV10015、PV10017、PV10018、PV10020、PV10021、PV10023、PV10024、PV10025、PV10029。它们恰好是 Retro Charts/DLC Songs 的数据库声明集；当前 include=[".", "Base Songs", "Restore Cut Songs"] 未启用 DLC Songs，正确排除，并非生成失败。

早期扁平发现308项存在F2nd物理pv_701被当成官方逻辑PV701的误配，不作为有效交付或安装。默认改用逐包权威映射，通用路径遇非零LYRIC缺文本时报错，不宣称无歌词。

安装是显式操作。先对所有新SRT验哈希与所有旧文件冲突预检；仅覆盖仍匹配旧安装清单哈希或与新文件完全相同的缓存。旧版无哈希 native-cache-manifest 不授权覆盖不同文件。自定义冲突请先人工备份移开。失效生成缓存只有仍匹配旧哈希时才回收；Ruby TSV和用户修改保留。

Python命令示例按项目要求用反斜杠展示；PowerShell实际运行请使用启动器，或把多行合并成一行。

```bash
python scripts/export_lyrics.py \
  --game-dir "E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus" \
  --output-dir artifacts/exported-lyrics
```

```bash
python scripts/export_lyrics.py \
  --source-manifest artifacts/installed-native-lyric-sources.json \
  --output-dir artifacts/exported-lyrics-advanced
```

```bash
python scripts/export_lyrics.py \
  --output-dir artifacts/exported-lyrics \
  --install-only \
  --install-dir "E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/lyrics"
```

```bash
python scripts/verify_lyrics_exporter_mvp.py
```

状态：LOGIC VERIFIED；没有部署游戏，最终MVP展示由用户验收，既有歌词功能验收状态保持不变。

成功快照发布在每次 cache/previous-cache/publish 移动和递归清理前核对解析路径仍位于 output_dir 内，拒绝符号链接和 Windows 联接点。定向验证包括真实 Windows 联接点，确认其指向的受保护文件保持完整。



最新定向验证已覆盖来源文本不一致时拒用该来源英文栏、Mod 英文翻译拒绝、lyric_id 跳号与重复、歌→うた/痛→いた/目覚→めざ的送り仮名后缀，以及 Ruby 成套安装、手工修订冲突保护和哈希篡改拒绝。测试命令：python scripts/verify_lyrics_exporter_mvp.py。

