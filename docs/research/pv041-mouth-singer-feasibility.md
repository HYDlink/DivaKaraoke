# PV041 口型与逐句歌姬配色可行性调查

日期：2026-10-13。本轮仅研究已经提取的资料，集中口型方向；不调查歌词自带颜色，不修改Mod、不实现自动识别、不新增游戏内存逆向或解包。

## 结论与边界

**口型方向有较强的实际数据基础，值得做单曲半自动实验。** 官方《カラフル×メロディ》（PV041）有869条带明确角色槽位的MOUTH_ANIM，呈现连续单槽、交替单槽、双槽近同时及同一句内换槽等结构。

直接数据是“哪个角色槽位何时收到哪种口型指令”；解释为“音频中谁正在唱”仍属推测。此次没有听辨音轨、逐帧核对画面或制作歌手真值，不能给准确率或宣称全曲通用。

建议后续最小路线：同来源口型证据 → 行级候选和异常提示 → 人工核对 → 配色。单槽清楚的行优先，句内交替、短动作、未知姿态保留复核；两槽都出现事件不等于整句共唱。本轮完成研究后停止，候选生成和渲染均未实现。

## 输入与原作者资料

资产就地读取，未复制提取树，未写游戏目录。完整文件大小、路径、SHA-256保存在 artifacts/pv041-mouth-research/evidence.json。

| 输入 | 路径或内容 | 核实结果 |
| --- | --- | --- |
| 官方文本表 | artifacts/main-region-extract/rom_steam_region/rom/pv_db.txt | Normal映射 rom/script/pv_041_normal.dsc |
| 官方DSC | F:/DivaKaraOkeLyrics/main-extract/rom/script/pv_041_normal.dsc | 61372字节；EAE075D12ABF48816A5AB2FB8B3A833FCA81715F63F2D70F12BB383ED4971E0E |
| 已有opcode表 | artifacts/Open-PD-Script-Editor/opcode_db/db.json | info_FT中MOUTH_ANIM为ID19、5参数 |
| 生产读取器 | scripts/extract_native_lyric_timeline.py | 原函数读取TIME/LYRIC/PV_END，研究只观察已解码局部变量 |
| 已有覆盖缓存 | artifacts/furigana-official-alignment/cache/PV041.json | 指向F2nd Song Pack物理PV709，而非官方PV041 |
| 覆盖DSC | 游戏mods/F2nd Song Pack/rom/script/pv_709_normal.dsc | 55260字节；EC49036BF4406D548D3517C17041D6BB9F42459CBBD8AE83A6D8D5DE463AA3C1 |

已安装 mods/MMFreeLyrics/lyrics/PV041.srt 与覆盖缓存同目录的SRT哈希一致：5B177B49B9E44DB8B2F1BB62B774F7C0B7DBC2C5E6745B2E181EC516C5C9D7C5。这证明当前磁盘歌词缓存的来源，不代表检查过当前游戏进程播放哪套PV。官方是主验证路径，覆盖版仅解释本机来源差异。

查阅的主要原作者资料：

- [Open-PD参数表](https://github.com/nastys/Open-PD-Script-Editor/blob/touchbar/opcode_db/db.json)：命令ID与长度。
- [Open-PD编辑界面及ID转换](https://github.com/nastys/Open-PD-Script-Editor/blob/touchbar/mainwindow.cpp)：MOUTH_ANIM第1参数为Performer，第3为Animation，第4为Transition；第2/5在该界面仍为未知。转换表包含新28→旧6，不能据此直接推导通用闭嘴ID。
- [Open-PD口型生成](https://github.com/nastys/Open-PD-Script-Editor/blob/touchbar/lipsync_midiseq.cpp)：支持显式performer的MOUTH_ANIM，也支持SET_CHARA后的EDIT_MOUTH_ANIM。
- [Project-DS底层笔记](https://github.com/Hydr8gon/Project-DS/blob/master/notes.txt)：TIME单位为十万分之一秒；列出相关口型命令，没有逐句歌手标签。
- [DivaDocs](https://docs.divamodarchive.com/DivaScript)：不同格式参数可能不同；PV_BRANCH_MODE的0/1/2为全局/失败/成功分支。当前页面没有完整MOUTH_ANIM语义，用户转述不作为已经验证的依据。

官方姿态为24/25/28/31/32，覆盖版为1/2/5/8/11/21/34/35，不可硬套相同编号表。研究只把官方28、覆盖版8作为“基准姿态”辅助统计，**未确认通用闭嘴状态，未生成静音区间或歌手标签。**

## 官方直接数据

官方文本表第2922–2930行确认槽0为MIK/VOCAL，槽1为RIN/VOCAL，performer.num=2。

Normal完整读取3803条命令、869条MOUTH_ANIM（初音槽444、铃槽425）、31条LYRIC。最后ID31文本为空，非空歌词30句。口型全部全局分支0，时间无回退；没有EDIT_MOUTH/EDIT_MOUTH_ANIM/SET_CHARA，本样本槽位可直接读第1参数。

同一PV的Easy/Hard/Extreme在时间、全部五参数和分支上与Normal的869条口型**完全一致**。不能外推到其他PV、版本或特殊难度。

| 歌词行 | 时间（秒） | 直接口型证据 | 候选解释，尚待听辨 |
| --- | --- | --- | --- |
| 1–4 | 13.097–33.854 | 仅槽0，逐句28/17/26/23条 | 初音独唱 |
| 5–8 | 33.854–53.637 | 仅槽1，逐句28/18/21/23条 | 铃独唱 |
| 9 | 53.637–60.448 | 两槽各27条；18条非28姿态均在20ms内同姿态配对 | 两人共唱 |
| 16 | 85.421–90.610 | 仅槽0，21条 | 初音独唱 |
| 17 | 90.610–95.799 | 仅槽1，21条 | 铃独唱 |
| 18 | 95.799–102.610 | 仅槽0，25条 | 初音独唱 |
| 19 | 102.610–106.502 | 仅槽1，10条 | 铃独唱 |
| 29 | 148.502–151.097 | 槽0有11条；槽1仅1条姿态28 | 不能因槽1单条事件判合唱 |

按非28姿态事件的纯描述统计，13句一个槽、17句两个槽都有，这不是歌手识别结果。第9/10/12/13/15/20/21/22/24/25/27/30句的槽0非28姿态都有20ms内同姿态槽1事件；第9句稳定相差10ms。20ms是研究辅助尺度，没有作为识别阈值。

单槽行首个非基准口型比歌词开始晚约100–131ms：首句LYRIC为13.09729s、初音口型为13.19729s，不能替换歌词起点或推断逐字时间。

## 可追溯真实样本

命令序号从1开始，偏移从文件0字节开始；完整五参数、TIME、分支与上下文见evidence.json。

| 秒 | 命令 | 序号 / 字节偏移 |
| --- | --- | --- |
| 13.19729 | MOUTH_ANIM(0,0,25,120,-1) | 181 / 2716 |
| 33.96405 | MOUTH_ANIM(1,0,25,120,-1) | 588 / 9368 |
| 53.73783 | MOUTH_ANIM(0,0,25,120,-1) | 972 / 15712 |
| 53.74783 | MOUTH_ANIM(1,0,25,120,-1) | 974 / 15744 |
| 150.39648 | MOUTH_ANIM(1,0,28,300,-1) | 3330 / 53916 |

第11句「アカ？　アオ？　シロ？　曖昧だね」（62.070–65.637s）的事件：

| 秒 | 槽位、姿态 | 直接观察 |
| --- | --- | --- |
| 62.17027 | 槽0、24 | 初音先有非基准事件 |
| 62.18027 | 槽1、28 | 铃为基准姿态 |
| 62.66675 | 槽1、24 | 随后铃有非基准事件 |
| 63.14324 | 槽0、31 | 再有初音事件 |
| 63.63972 | 槽1、24 | 再有铃事件 |
| 64.11621 / 64.12621 | 槽0/1、均31 | 后段近同时同姿态 |

这是句内口型交替及后段同步的证据；逐词对应谁唱仍需听辨，不能按字符比例切时间。

第14/26句也有共享开头与后续主要向不同槽发指令的结构；第28句开头同步、后续主要向铃发指令。第14句槽0在75.14324s收到24后，到78.06216s才收到28：**没有新事件不代表已闭嘴，保留非基准姿态也不代表仍在唱。** 事件密度法和持久张嘴状态法都有误判可能，本轮不重建渲染状态。

MIKU_DISP不能过滤声部：原版113.13333–117.63333s隐藏铃槽，但第21句（113.313–120.124s）仍有两槽完整口型。可见性与声部是不同数据。

## 当前覆盖版的额外歧义

重新解析PV709后的30句起止/ID/全文与既有PV041.json非空行完全一致。全部起点比官方缓存早8ms；最后一句结束为155.159s，对官方155.675s还有额外差异，不能只修统一偏移后混用。

覆盖版883条口型全部全局分支。文本表将铃写为performer.1.type=GUEST，但铃仍有大量口型，**只接受VOCAL会漏掉本机覆盖版的铃，type不能当跨包声部真值。**

覆盖版第3句新增铃的两条指令：

~~~text
24.31666s  MOUTH_ANIM(1,0,5,133,420)   序号312，偏移5236
25.41666s  MOUTH_ANIM(1,0,8,166,1000)  序号338，偏移5676
~~~

两者约相隔1.1s，原版此句只有初音口型。原因可能是演出、和声或移植差异，尚未验证，不能裁定为噪声或真实演唱。它是真实的“任意非基准动作即算参与”歧义样本。覆盖版在歌词出现前也有非基准口型，不能把口型事件直接当LYRIC的演唱起止。

## 验证、产物及复现

新增研究脚本 scripts/research_pv041_mouth.py，以临时行观察点记录现有read_lyric_events已经解码的局部变量，退出恢复原跟踪器，没有新写二进制遍历器。观察点变化时明确报错。这个方式仅作研究审计，不建议作为生产接口。

核对通过：命令长度加文件头覆盖文件全长；捕获的LYRIC/PV_END与原函数返回一致；同曲四难度口型全序列比较；覆盖来源重新关联30句与既有缓存一致；安装SRT与工作区哈希一致。空白ID31用于结束边界，不计演唱行。

**ANALYSIS VERIFIED；音频歌手身份 NOT VERIFIED；自动识别/配色 NOT IMPLEMENTED。** 未修改生产提取器、缓存格式、C++、DLL、Hook、配置或安装文件，架构未变，不增加架构决策。

artifacts/pv041-mouth-research/evidence.json 保存完整指令/偏移/哈希/分支/逐句证据，lines.md 保存官方和覆盖版各30句中文统计。重跑仅覆盖两份研究产物。

在项目根目录执行；反斜杠为Bash/Git Bash续行符（PowerShell交互需用反引号）：

~~~bash
python scripts/research_pv041_mouth.py \
  --active-cache artifacts/furigana-official-alignment/cache/PV041.json \
  --verify-other-difficulties
~~~

