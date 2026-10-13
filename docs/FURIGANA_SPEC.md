# 日文 KTV 振假名（Ruby）对齐规格

算法数据流与校验边界见 [平假名注音架构与算法](FURIGANA_ARCHITECTURE.md)；实际 PV 案例、已知陷阱和未解决样例见 [平假名注音案例与陷阱](FURIGANA_CASEBOOK.md)。

## 1. 目标

本规格定义 MMFreeLyrics 的日文 KTV Ruby 呈现。它面向横向 NicoKara 风格歌词：主歌词显示日文原文；仅对含汉字的底字组在上方显示平假名读音；读音跟随同一行的未唱/已唱色与ワイプ进度。

本功能不改变 SRT 时间线、不修改游戏 hook，也不在游戏进程中运行日文分词器。

## 2. 视觉规范

- Ruby 位于主字基线之上，字号为主歌词的 42%。
- Ruby 使用独立细描边：描边宽度为主描边的一半，至少 1 px；阴影位移按主阴影的 45% 缩放。
- 只为汉字或含汉字词组标注。原有平假名、片假名、拉丁字符、数字和符号不显示重复 Ruby。
- Ruby 的水平中心与所属底字组中心对齐。
- 当读音自然宽度大于底字组宽度时，等比例缩小 Ruby 直到不超过底字组宽度；不允许侵入相邻词或相邻汉字组。这采用 W3C Simple Ruby 的保守不悬挂策略。
- 连续汉字默认使用词组 Ruby。例如 昨日→きのう、宿題→しゅくだい、宇宙→そら。带送り仮名的词按汉字组拆开，例如 繰り返し→繰/く、返/かえ；描いた→描/えが。
- 当前演唱行的 Ruby 使用与主歌词相同的横向裁剪：裁剪左侧为已唱色，右侧为未唱色。下一行 Ruby 始终为未唱色。

这覆盖用户参考图中 僕→ぼく、描→えが、未来→みらい、遥→はる、遠→とお、道→みち、途→と、中→ちゅう、繰→く、返→かえ、心→こころ、試→ため、宇宙→そら 等形式。

## 3. 数据来源与优先级

1. 官方 DLC mdata_pv_db.txt 的 pv_NNN.lyric.NNN 为底字原文。
2. 同编号 pv_NNN.lyric_en.NNN 实际为官方罗马音唱法，而非英文翻译；它是歌曲唱法的最高优先级。
3. Janome 离线日文形态分析器只提供词边界和默认读音锚点。
4. 官方罗马音与词典读音不一致时，官方罗马音覆盖词典。例如 宇宙 在歌曲中可标为 そら，而非词典常规 うちゅう。
5. 无官方 Ruby 旁路数据时，DLL 仅显示主歌词，绝不阻塞模组或猜测并写入错误读音。

## 4. 旁路格式

每首歌与 PVNNN.srt 并列一个 PVNNN.ruby.tsv。第一列为从 1 开始的 SRT 行号；第二列用分号分隔 Ruby span：

```text
7    0:2:きのう;3:2:しゅくだい
```

单个 span 为 起始 Unicode 字符下标:底字长度:平假名。下标以主歌词 Unicode 字符计，不以 UTF-8 字节计。Ruby TSV 只补充排版数据，SRT 仍是唯一时间来源。

## 5. 生成与审计流程

1. 读取官方日文与同编号罗马音。
2. 用 Janome 分词确定词和送り仮名边界。
3. 将官方罗马音按词典读音锚点对齐到分词结果；不一致片段保留官方唱法。
4. 从每个含汉字词中剥离原本的假名，生成汉字组 Ruby span。
5. 输出 Ruby TSV，并同时输出 JSON 审计文件，供人工复核特殊唱法、歌词创意读法和分词歧义。
6. 将验证通过的 TSV 放入 mods/MMFreeLyrics/lyrics；DLL 载入同名 SRT 后可选读取它。

## 6. 验收

- PV424 的 53 行歌词均应保留原有时间与主文本。
- Ruby TSV 应产生词组 Ruby，且平/片假名行的 span 为空。
- 昨日の宿題必须得到 昨日→きのう、宿題→しゅくだい。
- Ruby 的任意自然宽度都不得压到相邻底字组；过宽时需缩放、保持居中。
- 当前行 Ruby 的已唱配色边界应与主歌词横向ワイプ边界一致；下一行不应提前变色。
- 缺失或格式错误的 Ruby TSV 不得让 MMFreeLyrics 或 DivaModLoader 失效。

## 7. 参考依据

- W3C Rules for Simple Placement of Japanese Ruby：https://www.w3.org/TR/simple-ruby/
- W3C Ruby Annotation：https://www.w3.org/TR/ruby/
- W3C CSS Ruby Layout：https://www.w3.org/TR/css-ruby-1/
- W3C Japanese Layout Requirements：https://www.w3.org/TR/2009/NOTE-jlreq-20090604/

规范采用 W3C 所述的 Ruby 作为读音标注、默认约半字号、组 Ruby 与熟语 Ruby 的概念；为保证动态 KTV 画面不重叠，本项目选择不向邻字悬挂的保守布局。
## 批量导出接线（2026-10-10）

旧实现已支持 Ruby 渲染，但只给 PV424 单独生成过旁路文件。新导出入口必须在有效来源覆盖、最终 SRT 时间线确定后生成每首 PVNNN.ruby.tsv 与 PVNNN.ruby.audit.json。旁路第一列对应最终 SRT 的有效非空连续行号，不直接使用原 lyric ID；同一歌词 ID 重复出现或编号跳跃也必须按时间线重排。SRT、注音和审计成套参与哈希清单、安装预检和用户文件保护，缺依赖或生成失败不得发布半套缓存。

最终时间线的 source.pv_db 顺序为匹配文本的查找依据。只有同 lyric ID 的日文原文与最终行完全一致，才允许使用其 lyric_en。英文栏必须与整句正文完整对齐，不能仅凭字段名称、词典相似度或局部命中就当成唱法。来源存在但失败时不回退发布词典读音；来源缺失时词典参考明确标为推测。词典仅辅助同音边界和等价长音拼写，不覆盖来源发音。详细算法与资源限制见 FURIGANA_ARCHITECTURE.md。

截图 PV809 已验证：声→こえ、震→ふる、伝→つた、愛→あい、詩→うた、呼→よ、奇跡→きせき；其中詩采用歌曲罗马音 uta 而非字典常见读音。实际视觉仍需用户验收。已验收或人工修改的旁路文件必须先检查差异并保留，不能为补齐批量注音而无条件覆盖。

已有缓存无需重新解包，使用短入口的 --rebuild-ruby-only 即可补齐。单首复核示例（换行展示，PowerShell 执行时可合为单行）：

```bash
python scripts/generate_furigana_sidecar.py \
  --timeline-json artifacts/exporter-mvp-final2/cache/PV809.json \
  --out-tsv artifacts/furigana-regression/PV809.ruby.tsv \
  --out-json artifacts/furigana-regression/PV809.ruby.audit.json
```