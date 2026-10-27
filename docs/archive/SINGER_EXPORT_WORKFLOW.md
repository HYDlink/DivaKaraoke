> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# 自动多歌手导出与人工修订

更新：2026-10-16。歌词导出默认自动扫描最终有效PV，不需要Agent或用户列出歌名。复用已解析资料，不重新解包；口型规则版本为mouth-activity-v2。

## 稀疏口型漏标修复

普通行仍默认要求6次活动，短于1.2秒的行至多3次。只有原本所有分支均未识别出歌手的整行，才启用补判：至少3次活动、至少2种有效姿态，活动跨度至少600毫秒且覆盖该行60%；或两个槽位至少3组同姿态事件一对一匹配，偏移不超过30毫秒、匹配率至少为较长序列的80%、跨度至少600毫秒且含至少2种姿态。成功/失败分支的最终身份必须一致。

已有主唱的行不走补判，避免把另一角色的少量呼唤动作加成合唱；没有口型或仅一次活动的回忆演出仍保持未知。补判不扩展姿态编号，不把未知编号当成已确认元音，不根据邻句继承歌手。审计以sparse_activity_proxy、逐槽sparse_support及profile.sparse_policy记录依据，仍是活动推测而非音频识别。

真实修复样本：PV212第10/22句「気持ちは今」每槽仅3–4次有效活动，第29句「させない　カラフル×セクシィ」每槽5次，其中5组在10毫秒内同步，现均保留LUK+MEI；PV041实际F2nd覆盖版第29句「楽しかったって」初音4次活动跨1671.62毫秒，覆盖2595毫秒歌词窗口的64.4%，现为MIK。两曲均不再有默认行，四难度结果一致。此修复不根据歌名硬编码身份。

## 日常使用

双击tools/export_lyrics.cmd：按当前DML启用状态、priority/include与逻辑/物理PV映射生成最终歌词、注音，再扫描角色身份。重复身份和PSEUDO_SAME复制槽归并；两个以上不同已知身份生成歌手标记。GUEST不直接过滤；尚未解释的复制类型和缺失身份保留在扫描报告，不猜角色。

默认只生成，显式安装时SRT、Ruby和歌手三件套按同一清单预检。用户修改过的任何安装文件会阻止整批覆盖；已失效且仍匹配生成哈希的旁路可回收。旧六曲MVP的明确哈希所有权会安全迁入新清单。

当前本机完整扫描309首，生成62首多身份候选、239首同身份跳过、8首角色资料不完整；另有一首已知两个身份但存在未解析槽，已保留该槽的不确定信息。这是角色/口型候选统计，不是62首都由这些角色实际发声的准确率结论。剧情无声动作、回忆演出缺口型等边界继续存在。

输出cache/singer-scan.json与singer-scan.md记录全部PV的自动选择、跳过或不明确原因；每首候选有singers.tsv、singers.audit.json、singers.md。缓存清单版本3同时记录安装文件哈希与选择结果。

## 人工标记：只改第四列

人工文件在输出目录manual-singers/PVnnn.singers.manual.tsv，与自动cache分开。第一次为每首候选生成模板；之后已有文件不覆盖，cache快照更新也不删除人工目录。五列依次为行号、开始毫秒、结束毫秒、人工歌手、歌词全文，只需改第四列。

| 第四列 | 含义 |
| --- | --- |
| auto | 沿用本次自动结果 |
| LEN | 镜音连 |
| KAI | KAITO |
| LEN,KAI | 两位参与，使用合唱样式 |
| - | 明确保留原默认色 |

其他身份：MIK初音、RIN镜音铃、LUK巡音、MEI为MEIKO；可使用合法的大写自定义身份。多人用英文逗号，不能重复身份。颜色仍在游戏Lyric面板配置，标记文件只记录身份。

《erase or zero》为PV728。第10句「踏み出せば、埋もれ　倒れても」对应模板中以10开头的记录，原第四列为auto；用户如确认连演唱，可自行改成LEN。其他列与文件首行保持原样。初始模板没有替用户填写任何人工声部。

修改后双击tools/apply_singer_marks.cmd：自动重算候选、套用人工修订并安装；不重建歌词和注音。重进PV或下次加载该曲时读取新标记。审计同时保留auto_singers/auto_reason及人工修订文件哈希，能够分辨自动推测与人工确认。人工行若曲号、总行数、时间或全文不再匹配，整次补齐拒绝发布，旧成功缓存保留。已有手改运行时singers.tsv也受安装冲突保护，推荐改独立manual文件。

本机已部署入口的人工文件位于游戏mods/MMFreeLyrics/artifacts/exported-lyrics/manual-singers/。工作区实验输出位于artifacts/singer-full-export/；两处为独立工具实例，可用manual-singers-dir显式共用同一人工目录。

## 可复用命令

以下反斜杠多行写法遵循项目文档约定，PowerShell实际执行请合并为一行或使用CMD入口。

完整导出（默认含自动歌手扫描）：

```bash
python scripts/export_lyrics.py \
  --game-dir "${game_dir}" \
  --output-dir artifacts/exported-lyrics
```

仅补齐歌手，保留SRT与Ruby：

```bash
python scripts/export_lyrics.py \
  --output-dir artifacts/exported-lyrics \
  --rebuild-singers-only
```

独立扫描已有缓存并提供人工目录：

```bash
python scripts/build_singer_timeline.py \
  --cache-dir artifacts/singer-full-export/cache \
  --output-dir artifacts/singer-preview \
  --manual-dir artifacts/singer-full-export/manual-singers \
  --verify-difficulties
```

逻辑验证：

```text
python scripts/verify_singer_export.py
python scripts/verify_lyrics_exporter_mvp.py
tools\build_lyric_playlist_regression.cmd artifacts\singer-full-export\cache
```

## 交付验证

默认完整导出与仅歌手补齐均已实际执行。全部62首旁路通过生产C++加载器和真实SRT绑定；309首逐行时间与正文保持一致，Ruby逐字节一致。完整重导有23份SRT仅补齐最后空cue的块分隔换行，文本/时间线未变化。人工单人、合唱、默认、错行拒绝、原自动证据保留、既有模板保护、旁路所有权迁移与用户手改冲突预检均通过。游戏内每首实际声部仍由用户体验，不将逻辑通过当成音频识别准确率。
