# DivaKaraoke v0.2.0发布整理（2026-10-26）

本发布工作区基于第二阶段ee5066b，独立于第三版开发。用户确认发布无逐字对齐的第二版；更名、许可证、新目录克隆构建、工具依赖下载与公开候选ZIP干净安装检查通过。发布前历史及源码未发现Git凭据，旧私有ZIP内OBS密码已排除。GitHub登录仍需完成，不能标记已上传。详情见RELEASE_V020.md与RELEASE_PRIVACY_AUDIT.md。

# 当前状态

## 第二阶段里程碑冻结，随后进入第三版（2026-10-25）

用户确认当前通过角色口型事件推测行级歌手归属、分歌手配色的成果为第二阶段完成里程碑，要求先归档和Git状态提交，含DLL/Mod/资源，再开始第三版全部逐字计划。本次冻结源码、已安装DLL/PDB和用户配置/歌词/字体/歌手资料；DLL与最近已验证构建同为9FD8A1F547259A7A1A59D96BB2591FE8ED08927395A438C0A05A94DEFB8F05CB。归档细节见RELEASE_V2.md，正式校验凭据为对应目录snapshot.json和release-v2.json。历史注音缺标、口型推测边界与OBS实机待办保留。归档完成前不修改第三版生产实现。

## 逐字歌词离线流水线与双层时间方案（2026-10-25）

用户明确以现有完善SRT为基础自动做歌词—口型对齐，要求制作步骤、离线脚本、字级渐变和明确时间精度，同时保留行级歌手/显示职责。已核对生产导出器、SRT/Ruby/歌手加载及裁剪代码，形成[实施方案](CHARACTER_TIMING_PLAN.md)：SRT继续行级主数据，新timing.tsv承载字/可信词组与Ruby发音段，audit.json保留证据；不把逐字拆成SRT cue，不依赖LLM逐句填时间。

方案固定导出/加载整数毫秒，保留DSC原始0.01ms事件；实际边界精度未知，P50≤50ms/P95≤100ms为待测研发目标，另报告覆盖/拒绝及开始结束误差。按C0合同、C1 PV045自动候选、C2真实边界、C3离线视觉、C4加载回归、C5导出安装、C6统一部署、C7来源扩展推进。已记录额外口型/促音/拖腔、终点、编号族、分支/多槽、UTF-16及现有读音缺口的处理边界；未来需要时离线音频补证，当前未选型或实现。**方案完成；生产逐字生成/加载/渲染NOT IMPLEMENTED，实际误差NOT VERIFIED。** 本轮只更新方案与交接，不改代码、歌词或游戏目录。

## 整句缺注音的安装态排查（2026-10-25）

用户PV812截图约37.74秒、第11句「ticktack ticktack 結んで開いて」没有Ruby。实际安装审计仍为整句来源对齐v2，来源是「TICK TOCK TICK TOCK musunde hiraite」，状态unmatched、spans为空，TSV有效行11也为空；不是仅凭截图推定渲染丢失。正文英文ticktack与来源ticktock存在拼写差异，当前Latin单元要求精确匹配，搜索在首单元失败（states=1），全句失败策略将后面的日文汉字也一并撤掉。第9句「ticktack ticktack 円を描いて」同类。词典已有むす/ひら参考，来源也有日文唱法，不是简单的“词典查不到”。

按当前已安装export-install-manifest逐曲只读统计：309首、9220个含汉字有效行，其中765行整句零注音，涉及174首；763行为unmatched，2行为ambiguous；另3行有局部未覆盖汉字。该统计不同于历史779个含汉字待复核行，后者也包含来源缺失的词典推测等。来源/规则失败不能等同于来源资料全部错误。证据artifacts/furigana-missing-review-20261025/installed-missing.json。

根因是前次安全策略的拒绝粒度过大，真实转写差异和不支持外来词也会导致整句缺标。后续应补有证据的英文/转写等价规则，并设计有可靠边界时的局部对齐，保留已确认汉字、仅隔离无法确定区段；禁止回到整句词典盲猜或任意跳过来源。本轮只读取现有缓存/代码并更新诊断文档，未改生成算法、SRT、Ruby、DLL或游戏目录，未执行新全量生成或部署。**ANALYSIS VERIFIED；覆盖修复NOT IMPLEMENTED。**

## PV045《Dear》口型到逐字时间可行性（2026-10-25）

按用户指定单曲只读复用官方资料，复用生产DSC观察回调完整读取2071条命令、524条口型；全部槽0/分支0，四难度口型时间/参数/分支完全一致。官方24句中17句在O/U归并后元音类别完整同序；前四句归纳候选表，其余20句13句同序，不当作音频准确率。首句17个口型可结合官方读音和既有正文映射关联到「あ・た・ま・の……」，頭对应三个读音。七句保留促音附近多事件、缺事件、姿态差异及末句A重复，不强补切点。

已确认当前生产渲染是整句时间线性推进全行裁剪边界；逐字变速可复用字体/裁剪，Ruby需独立读音进度。主要未解问题是动画命令与真实发声起止的偏差、长音/停顿终点、连续同元音与跨字读音；本曲23/24句首口型晚LYRIC100ms，另1句140ms，不能未经音频核对统一平移。新增scripts/research_pv045_mouth.py及单曲证据/首句候选，详见[可行性报告](research/pv045-character-timing-feasibility.md)。资料、四难度、正文读音关联与研究校验为ANALYSIS VERIFIED；真实发声时间NOT VERIFIED，逐字渲染NOT IMPLEMENTED。本轮未改生产C++、正式歌词、DLL或游戏目录。

## 单曲 PV 自然结束录制修复（2026-10-18）

DEPLOYMENT VERIFIED：用户退出游戏后已备份并直接安装DLL、匹配PDB及两份验收文档，4份文件SHA-256独立复核一致，5份配置保持原哈希。备份artifacts/deployment-backups/obs-single-end-20261018-011630；记录artifacts/obs-single-end/deployment.json；交付包DivaObsSingleEnd.zip。实际游戏单曲收尾与成片仍待用户验收。

用户反馈单曲播完停留结束画面时OBS仍录制，只能用单曲播放列表绕过。现场PV805日志确认：GameResultTask时钟冻结218.339秒、isPlaying仍为1，旧会话准备/录制均为1，直到PVsel才结束。当前最小修复直接识别已有GameResultTask，不需要播放列表或猜测终点。

ObsPvSession将GameResultTask纳入结束状态，清除active/prepared，冻结或残留递增时钟均不会重新启动。中途PAUSE_MENU_SWITCH继续录制，重播仍建立新epoch。既有ChangeGameState Hook仅将OBS结束通知提前到原函数前，准备通知仍在原函数后读取标题；未增加签名/Hook。后台用条件变量在快照变化时唤醒，保留每秒心跳，游戏线程不等待OBS。

生产ObsManager现场序列回放、结尾600帧/错误播放标记/重播/下一首、既有会话与所有协议字段、13项Helper模拟、歌词/歌手/缓存回归、Release/x64及DLL独立装载通过。DLL与匹配PDB位于artifacts/obs-single-end/build；DLL SHA-256：9FD8A1F547259A7A1A59D96BB2591FE8ED08927395A438C0A05A94DEFB8F05CB。BUILD / LOGIC VERIFIED；实际单曲收尾与成片尾帧仍为IN-GAME VERIFICATION REQUIRED。下一步普通单曲播到结束，不退出画面，确认OBS自动StopRecord保存；再验收人工暂停恢复与同曲重播。

OBS独立开发/验收文档已更新。此次按结果状态结束，未实现此前PV_END提前200毫秒预测；异步OBS响应仍可能保留少量结束画面，不声称帧精确截断。现有歌词视觉、音频控制、自动命名和Helper协议保持。
## PV730《Hello, Worker》履历随角色变化的只读核对（2026-10-16）

用户截图显示初音出镜，履历姓名为「初音ミク」且照片为初音。复用现有原版提取树，确认地区pv_db的pv_730默认performer为LUK、音源为rom/sound/song/pv_730.ogg、chreff默认引用EFFCHRPV730_LUK_001/002。main-farc-extract-v2/rom/auth_3d内已有MIK/LUK/RIN/LEN/KAI/MEI/HAK/NER/SAK/TET十种角色的001演出包；实际读取初音/巡音001的a3da，分别引用EFFCHRPV730MIK001_RIREKI__DIVSKN与EFFCHRPV730LUK001_RIREKI__DIVSKN，证实预制了角色专用履历对象演出资源。截图与资源支持履历随出镜角色匹配，不能据此推断实际音频换唱。

状态：资源存在及初音/巡音对象引用 **ANALYSIS VERIFIED**；未导出贴图逐像素对照，未追踪本机运行时具体选择函数，未验证每套服装的照片行为。仅只读核对与说明，无解包、代码变更或游戏目录写入。

## 伴奏例外正式名单与按曲提示已部署（2026-10-16）

用户完成实机测试并明确确认此前309首歌词曲库中的10首伴奏例外。正式入口新增docs/NON_VOCAL_SUPPORT.md，完整列出PVID/曲名/原因，区分用户已确认名单和其他结构扫描候选，并从README、NON_VOCAL_MVP及三功能验收说明直接链接；不再要求从artifacts查日常支持名单。

用户选择“播放到例外曲目时，在伴奏开关下显示一行提示”。NonVocalManager只在成功加载时按实际音频文件名匹配10个已确认默认音源，绑定/切歌/返回菜单时更新或清理，仅在PV工具面板伴奏开关下显示黄色“此曲无独立人声轨，伴奏模式无法去除歌声。”；普通音源无新增提示，不增加常驻列表或弹窗。不改音量控制、开关、OBS或Hook；换唱文件不凭PVID误标，已有性能修复的锁外UI逻辑保留。

Release/x64及独立DLL加载通过；28项文件名/路径/大小写/正常曲与换唱边界检查通过，正式名单与已审计10个默认文件一致，提示字形已有UI字符集覆盖。用户关闭窗口后残留PID21644未退出，首次部署未写文件；随后按用户明确授权仅结束该无窗口残留，再备份并直接部署DLL/PDB及三份文档，5份文件SHA-256独立复核一致，全部现有配置保持哈希。DLL：59D350AD217F9A29F45495481D19D6DEE0CB79DD508F3DDFD6FCAC0582623D0A。备份artifacts/deployment-backups/non-vocal-support-20261016-013433，记录artifacts/non-vocal-support/deployment.json，验证validation.json，包DivaNonVocalSupport.zip。**十首音频例外 IN-GAME VERIFIED（用户确认）；新提示 BUILD / LOGIC / DEPLOYMENT VERIFIED，实际显示仍待下次游戏确认。**

## 换句卡顿修复已获160 FPS实机确认（2026-10-16）

用户明确目标为开启歌词和录制时流畅，PV261可复现；关闭Show Lyrics仍卡，禁用整个Mod并重启后不再卡。静态审查确认旧原生捕获不受显示开关控制，每新句至少九次同步WriteConsoleW，且可能触发字体重建；这些数据已不参与正式KTV。已删除对应CopyChars/PVDB旧Hook和原生采集路径，整首SRT/Ruby字形预热保留。增加轨道/几何缓存及完整失效条件、Ruby UTF-8栈缓冲、OBS协议变化去重、音频面板锁外绘制/文件写入，并提前准备透明合成shader/纹理，保留原视觉算法。

Release/x64、独立DLL装载、播放列表/缓存失效、OBS全部协议字段与会话、真实DX11渐变/透明合成通过；首轮8张1080p/4K生产画面逐字节一致。新增真实PV261硬件DX11回放及ETW按需诊断，提供匹配Release PDB。Subagent二次只读复审未发现新增可复现正确性问题。离屏回放不含游戏负载/Present/控制台阻塞/OBS编码，不能替代实际卡顿调用栈。

用户催促先直接使用，已备份并部署7份文件且独立复核SHA-256；仅将Mod config.toml重新启用，freelyrics/歌手配色/音频/OBS配置哈希保持。DLL及符号见artifacts/performance-investigation/fixed-build，记录deployment.json，备份artifacts/deployment-backups/performance-fix-20261016-011259。BUILD / LOGIC / DEPLOYMENT VERIFIED。部署后用户明确反馈“明显好转，没有卡顿，开160Fps都没问题”，当前复测场景的游戏换句流畅度记为IN-GAME VERIFIED（用户确认）。此结论不扩大为全曲、所有输出分辨率或录像成片验收；录像是否仍有掉帧尚无单独反馈。

系统WPR19041普通权限报0xc5585011，管理员开始成功但保存报0x80010106，两次工具自检无有效ETL。微软签名PerfView已下载；新版WPT只选性能组件安装已成功，安装器退出码0；新版ETL保存尚未复测。没有PV261现场ETL或真实游戏火焰图，不能声称已经函数级定因。用户已确认160 FPS无卡顿，当前不再主动继续采集；诊断工具保留，只有后续复发或用户要求时再使用。详见PERFORMANCE_INVESTIGATION.md。

## 全曲库伴奏结构边界审计（2026-10-16）

按当前DML启用/优先级/include及11份PV数据库，审计329个默认PVID、45个显式换唱版本，共374条引用，去重349份原始音频全部按原采样率完整解码，定位/解码零失败；所有默认PVID均有可定位谱面引用，配置/数据库指纹在扫描期间一致。按PVID统计，不将共享音源或换唱当作不同歌曲数量；未逐项确认选曲界面显示。

默认20条结构性受限：7条目标人声组全零、13条双声道，物理去重19份；其中原309首歌词曲库有10条（6条空人声组、4条双声道）。45条换唱中22条受限（5条空人声组、17条双声道）；默认与换唱42条合计物理去重38份。其余309条默认/23条换唱仅为两组均有信号的候选，不能认定伴奏无和声、采样人声或未分离歌声。本次无整首无信号、保留组全空或同比例重复混音条目。

复用扩展`scripts/audit_non_vocal_audio.py`，新增`scripts/audit_installed_non_vocal.py`，保留来源指纹、默认/换唱区分、角色名称、整首声道统计与中文清单。报告`artifacts/non-vocal-library-audit/`；PV261/PV424与此前完整统计及源哈希相同，374条映射、汇总、脚本语法和UTF-8通过核验。漏按断人声可作游戏原声对照，但须关闭模组伴奏并以正常曲正对照；“没变化”单独不能证明无分轨，“主唱消失且伴奏保留”则说明同一音源有可独立控制信号。完整名单、其他边界及具体方法见[全曲库伴奏覆盖说明](research/non-vocal-library-coverage.md)。**音频结构 ANALYSIS VERIFIED；未执行游戏内听审、改Hook或部署DLL。**

## PV261《君の体温》伴奏模式残留人声原因已确认（2026-10-16）

用户截图中的伴奏开关已勾选，现有PV261日志也报告静音请求已应用。继续完整解码已有官方音频`F:/DivaKaraOkeLyrics/main-extract/rom_steam/rom/sound/song/pv_261.ogg`，确认Vorbis/44100 Hz/4声道/245.5秒：后两个声道（零基索引2/3，对应pair 1）各10826550个采样全部为零；前两个声道（pair 0）为唯一有效立体声。源文件SHA-256为9DB28999B9E0BC2DCAEA7823DA52A1B1CB74BAD44E7C19E4BC51E4A7955E545E。截图路径与此资源一致，Mod目录未发现同名OGG或CPK覆盖。

当前静音pair 1/3的逻辑对该四声道文件实际关闭的是空白pair 1，pair 3无对应源声道；结合用户仍能听到初音的实际反馈，人声与伴奏均已混入pair 0，无法通过当前声道增益独立关闭。静音pair 0会连伴奏一起关闭。四声道格式本身不能当作拥有独立伴奏/人声的证据，界面的“静音已请求”和录像后缀也不能当作听感证明。

新增只读脚本`scripts/audit_non_vocal_audio.py`以原采样率流式解码整首、记录逐声道非零计数/峰值/RMS及源文件哈希。对照PV424的168秒四声道音频，两组声道均有有效信号，排除审计流程将第二组声道统一丢弃的情况。报告`artifacts/pv261-audio-audit/channel-audit.json`，说明见[PV261音频证据](research/pv261-non-vocal-audio-evidence.md)。**音频源结构 ANALYSIS VERIFIED；此曲当前伴奏模式无法独立去人声，未修复或部署DLL。** 若需要纯伴奏，应另行使用可用的纯伴奏音源或离线音源分离；本轮检查不包含音源替换/分离。

## 稀疏口型导致默认色的修复（2026-10-16）

用户截图定位PV212第29句「させない　カラフル×セクシィ」与PV041实际F2nd覆盖版第29句「楽しかったって」。安装文件与自动结果一致、没有人工强制默认；根因是固定6次活动门槛：前者两槽各5次有效活动，后者初音4次，均被漏标。PV212另两处1363毫秒短句各槽3–4次，同样被拦截。

通用工具改为mouth-activity-v2，仅对原本所有分支均未知的行增加持续/双槽同步活动补判，不按PV硬编码、不扩展姿态、不继承邻句。PV212三处均恢复LUK+MEI，29/29行有标记；PV041该句恢复MIK，30/30行有标记。两曲四难度标签/歌词事件一致。普通主唱旁少量动作过滤、单次剧情动作拒绝、分支冲突、愛Dee39–42句组合与六初音归并重新运行当前分类器均通过；erase or zero第10句缺口型仍为未知。

全量重算309首、62首候选，68处原未知行获补判，涉及21首；原已识别身份均保持。新统计1213单人/693多人/604未知，不代表新增行已逐曲听审。62首生产C++加载绑定及导出器人工修订/安装保护回归通过；309首SRT、Ruby、既有人工模板、DLL与配色配置哈希保持。证据与逐行变化见artifacts/singer-threshold-fix/validation.json。LOGIC / DEPLOYMENT VERIFIED；已备份至artifacts/deployment-backups/singer-export-20261016-002023并直接更新工具、缓存和62首歌手标记，1113份运行时文件全部哈希一致。两首已安装旁路分别30/30、29/29行有身份，DLL、人工模板与配色保持原哈希。游戏当前运行，本次仅更新数据；重新进入PV加载，视觉仍待用户验收。另为部署PS1补充UTF-8 BOM，兼容Windows PowerShell中文文件识别。

## 跨项目游戏资产索引整理（2026-10-15）

用户准备在新项目预研其他Mod，明确与歌词几乎无关。新增docs/EXTRACTED_ASSETS_INDEX.md，核对基础包/DLC既有解包根、基础包/F2nd/Misaki-Max FARC展开根及历史报告（分别7659/528/77成功，报告均0失败）、实际a3da/bin样例和已有工具/DSC通用读取入口；区分已提取、结构解析与语义验证，未逐文件重新审计整树。EXTRACTED_ASSET_REUSE.md增加入口链接。只整理文档，不开新项目、不解包、不搬迁或写入游戏。

## 自动多歌手全量导出与人工修订已部署（2026-10-15）

用户明确授权：不再按Agent挑选的PV名单生成，自动扫描全部有效多身份PV并集成歌词导出；同时方便用户今后自行标注erase or zero。export_lyrics.py默认在最终来源合并与Ruby之后调用通用角色扫描/口型生成器，新增rebuild-singers-only短路；独立工具新增cache-dir批量入口，旧单曲接口仍可用。入口没有曲名/PV白名单。角色表按输入路径、mtime和size缓存，复制身份归并，GUEST不直接过滤。

实际9来源309首全部成功，工具自动生成62首多身份候选（2510行：1175单人、663多人、672未知），239首同身份跳过；8首因未解释的复制类型/身份不足保持不明确。另1首两个已知身份但存在未知槽，仍生成已知身份推测并记录槽位。此为候选与数据覆盖统计，不等同真实音频歌手准确率。角色/口型规则未改变，原上下试用配色与DLL保持原版本。

新增独立manual-singers/PVnnn.singers.manual.tsv模板，用户只改第四列auto、单人身份、逗号组合或-；已存在模板不覆盖。人工行严格绑定PVID、总行数、行号、时间和全文，错行拒绝整次发布；审计保留auto_singers/auto_reason与人工文件哈希。当前所有正式模板仍为auto，没有替用户写人工声部。apply_singer_marks.cmd可在真实安装位置一键重新应用并安装。

默认完整导出和仅歌手补齐均已执行；62首全部通过生产C++ SRT加载与绑定，独立全量SHA-256/时间/全文及人工覆盖/冲突保护/所有权回收回归通过。309首JSON时间线完全一致，Ruby逐字节一致；23份SRT仅补齐末尾空cue分隔换行。真实CMD入口在安装目录执行成功，1113份运行时文件与已安装缓存全部独立复核；三个CMD为UTF-8无BOM/CRLF。已备份并直接安装工具、62首三件套、309首可复用派生缓存及62份独立人工模板，回收旧同身份样本PV268的生成旁路；用户配置、字体、OBS与DLL保留。DLL仍FD686BCAD8CCACD3FF1C0F6B10A8241F799EAD50B4993BC8CA6F40DD67FE858E。

备份D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\deployment-backups\singer-export-20261015-202948；记录artifacts/singer-full-export/deployment.json及validation.json；包DivaSingerExport.zip。当前LOGIC / DEPLOYMENT / CMD VERIFIED，真实声部效果仍需用户体验。操作入口见docs/SINGER_EXPORT_WORKFLOW.md；安装人工目录为mods/MMFreeLyrics/artifacts/exported-lyrics/manual-singers。

## 合唱上下双色试用已部署（2026-10-14）

用户认可方案一的功能性，但明确视觉只是勉强、仍很可能以后改方案二；三个方案和图片已保存于docs/CHORUS_COLOR_DESIGNS.md。方案二原位置与预热省略号冲突，当前不实现也不移动省略号。方案一作为可回退试用默认，面板「上下双色」取消即回方案三整句横向渐变；独立chorus_vertical保存方向，旧配置缺键采用上下试用，四色与阴影保留。

共享singer_render.h使用既有ImGui精细裁剪生成字形上下色带，中间20%四段近似柔和过渡，正文与每段注音分别按真实高度取色。等色端点走原纯色路径；横向填唱、整体透明合成、字体图集、歌词与口型标签不变，无新shader或Hook。

两人/三人、完整四色及阴影、18/94/188字号、正文/注音的覆盖面积/UV/颜色、86400顶点跨16位索引偏移、原两字体/4K几何、DX11透明合成与方向持久化检查通过；最大透明合成误差1/255。Release/x64及DLL独立装载通过。用户退出游戏后已备份并直接部署15份文件，独立再次复核哈希一致。DLL SHA-256：FD686BCAD8CCACD3FF1C0F6B10A8241F799EAD50B4993BC8CA6F40DD67FE858E；备份：D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\deployment-backups\singer-mvp-20261014-011832；记录artifacts/singer-mvp/vertical-deployment.json，验证vertical-validation.json，包DivaSingerColors-MVP.zip。BUILD / LOGIC / DEPLOYMENT VERIFIED；上下视觉IN-GAME VERIFICATION REQUIRED。

## erase or zero回忆演出漏标确认（2026-10-14）

用户截图并确认第10句「踏み出せば、埋もれ　倒れても」实际由镜音连演唱，但这一段为回忆演出，没有对应的歌唱口型序列；用户接受这是口型方案的特殊边界。现有审计26.426–32.079秒只有LEN一次候选活动、KAI零次，跨度零，不满足阈值；下一句「ピュアな自由に」有LEN九次连续活动并正确标为LEN。安装旁路与工作区SHA-256一致，第10句明确为未知，故截图默认色来自证据不足，不是部署遗漏或渲染错色。

本轮只记录用户声部真值与现有事件的差别，不降低阈值、不把邻句身份强行传播、不手改安装旁路。此类漏标与此前「无声却有口型」的误判是两种独立局限；没有口型不能推出没有歌声。若未来要求覆盖，需要另行取得音频或可信声部分工资料。当前算法及DLL保持原样。

## 合唱句首辨识方案评审（2026-10-14）

用户提供《カラフル×メロディ》三张实际游戏截图并认可MVP效果；可确认双歌手配色、颜色面板和整句横向合唱渐变已在游戏显示。此确认限于截图中的视觉效果，不扩大为六曲音频声部识别准确率验收。

当前横向渐变的句首近似单人色，用户希望从开头辨识合唱。本轮提供可调填唱进度的上下双色窄过渡、句首双色标记及现有横向方案对比，并按用户要求导出三张方案图片；推荐双人先评估上下双色，三人以上可用句首组合标记避免细条纹。预览使用模拟背景与系统字体，不是已部署效果。浏览器736/320宽度、填唱进度与方案切换通过，仅设计评审，未更改或部署DLL。实际上下效果仍待用户选择与游戏验证；窄过渡实现需分割字形四边形并插值UV，单纯改顶点Y取色只能产生四边形内线性插值，不能直接复制预览中的窄过渡带。

## 逐行歌手四色与合唱渐变MVP交付（本轮）

按用户最新授权实现并直接部署。Promise确认为RIN+MIK（本机F2nd物理PV770覆盖）；erase or zero确认为LEN+KAI，第三槽是LEN复制，不新增身份；ACUTE支持KAI/MIK/LUK；Catch the Wave六个演出槽合并为MIK。通用 scripts/build_singer_timeline.py 从已有缓存来源自动生成 singers.tsv/audit/中文结果，不解包、不依赖Agent。生产DSC读取器仅增加可选已解码命令观察回调，保持原返回值。

普通行默认6次活动、短行至多3次，并检查跨度、相对占比、成功/失败分支一致性；来源专用高频姿态保留推测说明。六首各难度标签一致；愛Dee恰好39–42句双人，与用户校对一致；erase or zero的62句中23单人/10多人/29默认，用户确认剧情MV有无声口型，不能把其标签称为已验证音频歌手。此数据用于误判对照，不进一步扩展字级对齐或音频识别。

Lyric颜色面板新增按身份的歌手配置，当前第一、第二歌手默认展开，完整未唱/已唱填充及描边四类颜色另带两种阴影；独立 singer-colors.toml 原子保存，可支持任意身份数量与特定多人组合。合唱采用两端保留原色、中间30%柔和渐变，可切平均融合纯色；正文/Ruby共享整行顶点渐变坐标，保留字体UV、ワイプ裁剪和透明合成。旁路PVID/行数/时间/全文严格匹配，错行文件整体拒绝，缺失或未知沿用旧默认色；切歌不沿用旧身份。

Python真实/隔离样本、生产SRT六曲绑定与播放列表、四色配置持久化、自定义第三身份、18/94/188字号字形/渐变UV/三人组合/原DX11透明合成、Release/x64和最终DLL独立装载通过。**BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED；IN-GAME VERIFICATION REQUIRED。** 最终DLL SHA-256：01F2C9E562671C954B83BAA3E6178F0F402E2A9F341F69DC97192560A7554E21。

游戏未运行时已备份并直接安装DLL、六首歌手旁路、三份工具和说明，共11份文件SHA-256核对一致；备份 artifacts/deployment-backups/singer-mvp-20261014-003456；记录 artifacts/singer-mvp/deployment.json，实验包 artifacts/singer-mvp/DivaSingerColors-MVP.zip。字幕/Ruby、字体、原配色、OBS及用户配置保留，无签名/Hook/结构偏移变更。快速体验按Ctrl+G，先Promise及已校对愛Dee，再以erase or zero观察误判。使用与复现见 [歌手配色MVP](SINGER_COLORS_MVP.md)。



## 愛Dee（PV802）全自动歌姬配色口型研究（2026-10-13）

用户希望完全自动化，指定愛Dee继续解析；不把人工修订当成必经步骤。本机曲名核实为PV802（PV809是愛の詩），读取已安装X Song Pack的现有脚本/文本与缓存，明确不是官方MM+原版证明。Normal完整4694命令、1165条口型（初音821/巡音344）、48句缓存重建一致，安装SRT哈希一致；四难度口型全序列一致、全局分支、无时间回退或隐式口型。

工具参考元音映射来自已有Open-PD头文件，34/35保持未知。零裁边下21句只有初音元音、13句只有巡音元音、14句双槽，不是识别正确率。巡音说唱可见连续单槽；部分日文行巡音只有未知34或M动作，不能任意口型都判合唱。口型可早于对应字幕46ms至544ms，固定裁边敏感；142–157s日文加括号英文有两套不同步元音序列，支持不同词重叠候选，尚未听辨主唱/和声。无字幕空档及末句后仍有口型，不能判纯伴奏或伪造歌词。

新脚本 scripts/research_pv802_mouth.py 复用现有读取器/观察器，不重写DSC parser；证据和48句统计在 artifacts/pv802-mouth-research/，详见 [愛Dee口型研究](research/pv802-mouth-singer-feasibility.md)。可继续探索自动单槽/双槽/不明确分类，以双人色或默认色处理混合行；不承诺每词唯一正确声部。**ANALYSIS VERIFIED；音频角色与准确率 NOT VERIFIED；自动配色 NOT IMPLEMENTED。** 未改Mod、已部署缓存、生产解析器、游戏文件或内存集成。



## PV041 逐句歌姬配色口型调查（2026-10-13）

按用户选择仅研究口型，复用已提取官方《カラフル×メロディ》PV041：Normal 3803条命令、869条带槽位口型（初音444/铃425）、30句非空歌词，口型全部全局分支；Easy/Hard/Extreme口型全序列与Normal一致。前四句仅初音槽、后四句仅铃槽，副歌有稳定相差10ms的同姿态双槽指令；同一句内也存在交替与后段同步，不能把两槽事件等同于整句共唱。基准姿态28尚未确认为通用闭嘴状态，未生成歌手标注或静音区间。

发现已生成/已安装PV041歌词来自F2nd Song Pack的物理PV709覆盖脚本（883条口型），不是官方原版；现有30句重新关联一致，安装SRT与工作区SHA-256一致。覆盖表将铃标为GUEST却仍有大量口型，第3句比官方增加铃约1.1s的动作，原因未验证，不能凭type或任意事件判定声部。仅作本机来源差异核对，官方仍为主证据。

新增 scripts/research_pv041_mouth.py，以临时行观察点记录现有解析函数已解码局部变量，不重写DSC parser；完整指令/偏移/哈希/分支及逐句统计保存在 artifacts/pv041-mouth-research/。样本与结论见 [PV041口型可行性研究](research/pv041-mouth-singer-feasibility.md)。**ANALYSIS VERIFIED；音频歌手身份 NOT VERIFIED；自动识别/配色 NOT IMPLEMENTED。** 未修改生产提取器、C++、DLL、已有缓存、游戏配置或安装文件，未解包或新增内存逆向。本轮研究完成后停止。



## 本地录制展示里程碑保存（2026-10-13）

用户确认当前实际功能已可用于录制展示，要求保存阶段性版本。工作目录原本已有 MMFreeLyrics Git 仓库，但仍停在上游 86ca982，累计功能、工具及文档未提交。本阶段以本地 codex/recording-milestone-20261013 分支和 recording-ready-20261013 标签保存源码，更新 ImGui/公开 SRT parser 子模块固定版本，保留上游历史，不发布 GitHub。

完善 .gitignore，区分源码与解包/历史 artifacts、第三方离线库、编译缓存及私人 OBS 配置，不删除原文件。新增 tools/save_local_snapshot.ps1，只读安装目录，保存实际 DLL、歌词、字体、配置、离线工具与编译依赖，逐文件核对 ZIP 内容 SHA-256 并验证主仓库 Git bundle；完整快照以 artifacts/local-snapshots/recording-ready-20261013/snapshot.json 为完成凭据。范围与恢复操作见 docs/LOCAL_VERSIONING.md。

已安装 DLL 哈希 D14B37B870DAD217B2F626CA40E10AC3CE988C56587583E0AD6250DFE20B7832 与最近部署记录一致。本轮只做版本保存，不改产品功能、不重跑游戏/OBS、不替换安装文件。用户认可的录制展示可用记为阶段性验收，历史待办及全曲读音复核不自动关闭。上游许可继续待确认，私有恢复包可能含 OBS 密码，Git 忽略该目录；游戏和外部解包资料保留原处。同盘快照不能替代异地备份。


## OBS 双击启动器闪退修复（2026-10-12）

用户截图中的乱码/命令截断已在真实CMD复现（退出码9009）：源码和安装版启动器均为UTF-8无BOM，但9处独立LF、仅1处CRLF，CMD错误解析中文行及后续python/pause。此前后台直接运行Python的成功不能作为双击CMD入口的验收。

已将 `tools/start_obs_helper.cmd` 统一为UTF-8无BOM、40行CRLF、独立LF为0；增加固定中文窗口标题、进入脚本目录、实际Python 3可执行检查及py.exe后备、缺文件/缺Python中文提示和暂停显示。 `.gitattributes` 为CMD/BAT指定CRLF；后续编辑仍须核对实际文件字节，不只检查UTF-8编码。

帮助模式退出0、缺配置退出1、缺Python退出2、缺助手退出3均在CMD验证；中文正常且错误留有提示。已备份并直接替换游戏已安装启动器，正常用户环境中的安装入口--help通过，源文件/安装SHA-256一致：`6BC7FA608EA98D98C785B8698FA2C1F36ADF201137CA790D2140D7232ACF1259`。通过正式CMD入口已启动Helper（本轮PID23836）；正常用户管道验证及OBS认证检查通过，未创建测试录像，无需重启游戏或替换DLL。备份/记录见 `artifacts/obs-launcher-validation/deployment.json`，验证见同目录 `validation.json`。测试临时启动器/脚本目录已清理，不增加日常入口。

**CMD VERIFIED / DEPLOYMENT VERIFIED / HELPER START VERIFIED**；用户日常双击及游戏面板再次连接仍由用户实际确认，录制内容未用于本轮验收。游戏OBS配置、密码和新On Vocal/Off Vocal命名Helper保持现有版本。


## 游戏启动调试控制台检查（2026-10-12）

只读确认本机游戏根目录 `config.toml` 当前设置 `console = true`，游戏启动控制台由 DivaModLoader 配置启用；项目 Source 未调用 AllocConsole/AttachConsole，LOG 只向已有标准输出写入。`freelyrics-diagnostics.log` 中的签名地址和初始化阶段通过独立文件流写入，不依赖控制台窗口。

日常使用建议关闭加载器控制台、保留轻量文件诊断；无需删除启动排障期间修复的延后初始化、签名检查和安全退出。OBS Helper 的命令窗口承载自动录制进程，应独立处理；直接关闭窗口会退出 Helper，不能作为普通调试窗口一并关闭。本轮仅检查并回答是否应关闭，未修改游戏配置、DLL 或 Helper，控制台关闭后的游戏启动尚未验证。


## OBS 录制文件后缀修订（2026-10-12）

按用户要求，将录制文件格式由 `歌曲名 [On Vocal/Non Vocal]` 改为 `%s-On Vocal` / `%s-Off Vocal`（如 `恋愛裁判-On Vocal.mkv`、`愛Dee-Off Vocal.mkv`）。保留曲名清理、空标题 PVID 后备、重名序号与录制生命周期，仅修改 `tools/obs_helper.py` 的命名字符串；同步既有模拟与真实 OBS 验证脚本的预期及 OBS_CONNECTOR 说明。

13 项现有 Helper 模拟回归通过，未连接 OBS 或启动真实录像。确认游戏和 Helper 均未运行后，备份并直接替换游戏已安装 Helper，源码与安装 SHA-256 一致：`B8803DE0730AEF253C3D791C5EB2DD14417F7D4EC31C53A296B0634BA0B03591`。备份：`artifacts/deployment-backups/obs-filename-20261012-231532`；命名修订包和部署记录：`artifacts/obs-filename-delivery/`。此次无需构建或替换 DLL。下次通过原安装入口启动 Helper 后使用新格式；历史录像不改名。**LOGIC VERIFIED / DEPLOYMENT VERIFIED；新格式真实游戏录像仍为 IN-GAME VERIFICATION REQUIRED。**


## OBS 连接恢复与工具冗余审计（2026-10-11）

助手在工具隔离环境内启动的 Helper 虽有进程和管道，正常游戏环境访问却返回拒绝访问。已结束本轮该进程，改在正常用户环境隐藏后台启动 Helper（本轮 PID 18232），正常环境管道请求/回复通过，用户确认游戏连接成功。此前单独 OBS WebSocket 认证通过不能证明游戏 IPC 连通。**IN-GAME CONNECTION VERIFIED**；此次连接恢复不代表录制首尾验收完成。

用户开始录制后，后续仅查文件与更新文档，未操作窗口、重启进程、发送连接探针或改游戏安装文件。日常唯一入口明确为游戏 `mods/MMFreeLyrics/tools/start_obs_helper.cmd`，正常双击启动，控制台窗口保持打开；Helper 未退出时游戏重启无需重开，电脑重启/关闭 Helper 后需再次启动。目前无自动启动和一键重启机制。

项目源码及历史工具副本按 SHA-256 审计：`scripts/tools` 有27个自有 Python/命令文件，源码文件内容重复组0；20个源文件在 artifacts 中有34份额外同名副本，其中19份与当前源码相同、15份不同。项目内3份 `start_obs_helper.cmd` 完全相同，来源为源码、旧MVP包和OBS发布包；旧MVP包的 Helper 只支持v1，当前游戏发送v2，存在误启动旧版本风险。源码/两个包均未包含本机私有配置，不能代替已配置的安装入口。

`tools/scripts` 另有99份可重新生成的 Python缓存，共89.64 MiB；OBS第三方依赖测试目录19份文件约155.6 KiB；GameConsoleReader包含编译中间产物。多层歌词构建脚本有实际调用链，不能因名称近似就删除。完整文件/哈希清单：`artifacts/tooling-audit/inventory.json`。本轮为审计，未清理历史发布包、回滚备份或缓存。入口整理和按引用清理待单独实施。


## 注音来源优先重构与全量部署（2026-10-11）

复审确认旧流程存在词典默认读音覆盖唱法、60%相似度门槛、局部贪心错切、失败后词典补猜、未知英文占位及单纯覆盖审计漏报等漏洞。新增独立 `scripts/furigana_alignment.py`，改为固定正文约束下整句消费来源；词典只辅助同音切点/等价表记，来源存在但无法对齐不发布词典猜读，歧义明确保留。搜索保存最优边图并清理逐行缓存，跨行缓存256；受监控全量导出峰值约 143.8 MiB，未触发384 MiB中止阈值。此前电脑卡死原因尚未确认，不能据本次测量断言与此前任务无关。

18个典型/真实句与拒绝猜读回归、导出器MVP均通过；实际缓存PV049/PV095有效行号、PV096近=ちか、PV824一歩=いっぽ、PV249君=きみ/五个恋各こい、PV255一人=ひとり、PV253破=やぶ/眠=ねむ核对通过。连续同ID同全文、间隔-100至250ms归并不限制首段长度，PV249长段重复也已合并。没有按PV事后改注音输出。

全量309首、20941个跨度，较旧EOF修复基线有2397行变化；779个含汉字行仍待复核。来源缺失、源词/正文差异、不支持转写和歧义需要继续处理；不能宣称309首每个唱法均正确，或将减少猜读后的缺标视为已完成读音审核。全部变化及待复核见 `artifacts/furigana-official-alignment/review.json`，309首可读稿见同目录 `readable/README.md`。

游戏未运行时已备份并直接安装927份缓存与8份脚本，全部SHA-256核验一致；旧所有权清单失同步，927份当前文件均逐份匹配已验证历史生成缓存后才迁移归属。备份：`D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\deployment-backups\furigana-alignment-20261011-231611`。保留隔壁已部署DLL，SHA-256 `D14B37B870DAD217B2F626CA40E10AC3CE988C56587583E0AD6250DFE20B7832`；本次离线生成/缓存修复不需修改DLL。安装后的实际加载309首已用生产SubRipParser复验，有效行数/末句差异0；安装脚本回归也通过。目录73份不补零旧副本不在运行时PV%03d路径内，未当成活动文件验收。

**LOGIC VERIFIED / DEPLOYMENT VERIFIED；完整唱法人工复核未完成，IN-GAME VERIFICATION REQUIRED。** 架构/案例/规格及持久决策D013同步更新。下方“PV255尚未修复、缓存待部署”等是早期记录，已由本节替代。

## 平假名注音文档整理（2026-10-11）

新增 [FURIGANA_ARCHITECTURE.md](FURIGANA_ARCHITECTURE.md) 说明离线输入、Janome/罗马音锚点对齐、有效行号、Ruby TSV、审计和运行时边界；新增 [FURIGANA_CASEBOOK.md](FURIGANA_CASEBOOK.md) 归档 PV049/PV095 行号错位、PV249 君与重复恋、PV253 短重复与混合词、PV014/PV052 锚点陷阱及 PV096/PV255 待复核问题。文档明确区分逻辑夹具、读音人工复核和游戏内验收。

复核时发现 PV255「一人きり」当前校对稿仍生成 `一人《いちにん》`，而同源罗马音为 `hitori kiri`；这是已知但尚未修复的读音错误。全量 Ruby 不能因此标记为逐行正确，后续生成器全量修改和部署需先补回归、复审缓存差异。文档更新不改变游戏文件；现有工作区候选缓存尚未部署，用户游戏内验收仍进行中。

## PV 播放列表歌词串曲修复（2026-10-11）

已定位根因：LyricManager 只在 displayStatus != OnScreen 时处理 PV POST PROCESS TASK；播放列表切歌没有先返回 PVsel，第二首准备事件被跳过，旧 SRT 与 Ruby 继续使用。运行日志中 OBS 已识别 PV249 → PV253，但歌词加载日志没有对应 PV253，符合这一触发路径。

每次 PV 准备完成均重建对应 SRT/Ruby 时间线与索引；PV_STAGE、PV_WATCH、PVsel 及菜单状态清理旧数据。时间线增加 loadedPvid 绑定，PVID 提前改变时立即禁止渲染并逐帧清空，避免加载通知到来前串曲。同曲重复准备也重新加载；暂停保留本曲；缺失或无效 SRT 不显示上一首。未新增游戏签名/Hook，未改变歌词排版、演唱时间或 OBS 控制行为。

直接编译生产 LyricManager 与真实 SRT/Ruby parser 的隔离回归通过：两首不经 PVsel 连播、Ruby 切换、提前 PVID、加载状态清理、同曲循环、暂停、缺失/无效文件及空选曲；OBS 会话回归、Release/x64 和独立 DLL 装载通过。复现入口：tools\build_lyric_playlist_regression.cmd。BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED；两首真实游戏播放与循环仍为 IN-GAME VERIFICATION REQUIRED。

游戏退出后已备份并直接部署 DLL，构建产物与安装文件 SHA-256 一致：D14B37B870DAD217B2F626CA40E10AC3CE988C56587583E0AD6250DFE20B7832。旧 DLL 备份：游戏模组 backup/2026-10-11-124750-lyric-playlist；部署记录 artifacts/lyric-playlist-delivery/deployment.json。用户歌词、字体与配置保留。下一步用两首歌词明显不同的 PV 验收第二首及其振假名，再观察同曲循环；之前 OBS 提前收尾方案仍为 NOT IMPLEMENTED。

## OBS PV 尾部加载闪帧调查（2026-10-11）

已只读分析用户 PV249《アゲアゲアゲイン》录像：60 fps、224.150 秒，最后 4 帧约 66.7 ms 出现下一首加载界面，之前约 1.93 秒黑场。运行日志证实原逻辑等待 PVID 变到下一首才结束录制；PV249 已停在 223.018 秒，isPlaying 仍为 1。复用已提取 DSC 与既有读取函数确认 PV_END=223.000 秒；末句结束为 202.577 秒，不能用于录制收尾。

建议以可靠 PV_END 为准提前 200 ms 停止（PV249 222.800 秒），配可调提前量、会话自然停止锁和即时 IPC 唤醒；无可靠终点保留原后备。详见 [OBS_CONNECTOR.md](OBS_CONNECTOR.md) 尾部调查。ANALYSIS VERIFIED / NOT IMPLEMENTED；本轮未改代码、录像或配置，游戏仍运行，未部署。下一项为按原生终点实现与同曲/两首游戏验收。

## OBS 自动命名与播放列表逐首录制（2026-10-11）

新增独立开发/验收文档 [OBS_CONNECTOR.md](OBS_CONNECTOR.md)。游戏当前曲名与实际人声静音状态经 v2 IPC 传入 Helper，录制前设置曲名 [On Vocal/Non Vocal]，重名加序号，处理非法字符与 OBS 模板转义；结束确认 outputPath 和完全停止，再恢复原模板、继续待命。模板恢复有本机持久记录，保留人工录制所有权边界。

复用已有状态和歌曲加载通知，补齐不经 PVsel 的切歌/同曲循环；旧时钟须归零后递增，暂停不分文件。后台日志增加 PVID、GameState、时钟、isPlaying 和会话采样。不新增游戏签名/Hook，不修改歌词或音频增益行为。

13 项 Helper 模拟、C++ 会话回归、Release/x64、独立 DLL 装载通过；真实 OBS 30.1.2 / WebSocket 5.4.2 两段短录制确认独立日文文件名、两种后缀、非空 MKV 与原模板恢复。发现并修复 StopRecord 返回路径后尚未封装完成的切歌竞争。BUILD VERIFIED / LOGIC VERIFIED / OBS VERIFIED；真实游戏播放列表、末曲自然结束与视频首尾仍为 IN-GAME VERIFICATION REQUIRED。统一 DLL SHA-256：83E4B997E2696694A1C3D0689A1B0A156D37CBCF7ACFC78F448C4EB1A21A618B。DEPLOYMENT VERIFIED：已备份并直接替换本机 DLL、Helper 与 35 个依赖文件，SHA-256 一致；备份为游戏模组 backup/2026-10-11-112522-obs-playlist。新版 Helper 后台已启动，实际管道和 OBS 认证通过；用户配置、密码、字体和歌词缓存保留。此次统一 DLL 保留当前工作树已完成的段落布局和长句适配等歌词改动，本轮未修改其歌词代码。

## 长句临时缩字号与累计修复部署（2026-10-11）

按用户最新选择实现运行时整句宽度适配：依据实际字形、Ruby、描边、阴影、背景、窗口分辨率和镜像安全边距测量，超宽句临时缩小到能完整显示；普通句保持用户 94 号设置。当前句与预显示下一句各自独立适配，预告、开唱、保留与淡出保持相同几何；整句起止时间、Ruby 索引和均匀ワイプ时间不变。先前 85% 下限/语义拆片建议由此选择替代，语义拆片未实现。

截图对应 PV095 第 7 句（32.812–37.312 秒）。真实 EPSON / DFP 字形检查下，1080p、94 号、8% 边距的长句临时约 80.12 / 91.05；后句仍为 94。两种字体、上下轨、Ruby、描边、背景、负向阴影及 4K 边界检查通过。PV824 段落重置及 DX11 真实透明合成回归通过，最大 RGB 误差 1/255。可重复检查入口：tools\build_ktv_render_regression.cmd。

已在确认游戏退出后备份并直接部署累计新版 DLL：artifacts/lyric-width-fit-build/MMFreeLyrics.dll；部署与构建 SHA-256 一致：93C29849792AD91234DA9488B878147200E72DE20449C096701F35450D46F9A8。旧版备份：游戏模组 backup/2026-10-11-112051-width-fit；验收包：artifacts/lyric-width-fit-delivery/歌词长句适配累计修复.zip。该版包含上一轮尚未部署的段落重置和提示点跟随修复，先前“游戏仍运行/待部署”记录为历史状态。

显示规范已更新 KTV_SPEC.md，架构共享几何与持久决策已记录。BUILD VERIFIED / LOGIC VERIFIED / RENDER VERIFIED / DEPLOYMENT VERIFIED；PV095 字号及 PV824 段落画面仍为 IN-GAME VERIFICATION REQUIRED。

## 段落重置、提示点跟随与长句设计（2026-10-11）

用户截图定位为 PV824 第 20 句，开始 1:58.538，前段第 19 句结束 1:43.992，空档 14.546 秒。已将全曲行号交替改为段落内交替：空档至少 8000 ms 时首句固定回上轨、第二句下轨；短停顿继续交替，提示点跟随紧接下来要唱的行及其文本起点。淡入、淡出和真实同轨占用使用同一份布局。

PV824 真实 SRT、奇偶段落、短停顿提示点、安全边距及较大预显示阈值检查通过；DX11 整体透明合成回归保持最大 RGB 误差 1/255。Release/x64 与独立装载通过；待部署 DLL：artifacts/lyric-paragraph-fix-build/MMFreeLyrics.dll，SHA-256 CE96A9A46E9FBBDAC18285718433FD5CDB301464AB2B35B4A95E34F31A763198。

已统一更新 [KTV_SPEC.md](KTV_SPEC.md)，整合六秒预告、小点 1.5 倍与描边、0.5 秒整体透明过渡、1.5 秒正常停留、最终已唱颜色保留、Ruby、分段固定位置及提示点归属。长句方案为按实际字形宽度限制、轻微超宽最多缩小约 15%、明显超宽按语义及可信演唱切点分片；仅设计记录，NOT IMPLEMENTED，未修改字号、SRT 或 Ruby。

游戏仍运行（PID 38600），用户明确选择“暂时继续运行”。本轮不替换游戏 DLL，部署待正常退出后由主编排备份、直接替换并核验 SHA-256。当前游戏保留上一版 E4354834933B210133ADC52E710C1EFFF5411F9E5142212358836079E85B64EA。BUILD VERIFIED / LOGIC VERIFIED / RENDER VERIFIED；新布局 DEPLOYMENT PENDING / IN-GAME VERIFICATION REQUIRED。

## 歌词透明过渡纠正（2026-10-11）

已纠正逐层描边透明度叠加造成的黑底显影：主歌词、描边、阴影、Ruby 和背景先在 DX11 透明画布内合成，再以预乘透明方式整体混合回原画布。已唱与未唱区域采用互不重叠的裁剪；结束后保持最终ワイプ和 Ruby 配色，不重置为未唱状态。

每句按独立时间窗口绘制，正常保留 1.5 秒，再淡出 0.5 秒；同轨旧句淡完后新句淡入 0.5 秒。密集短句缩短停留以给后句留出过渡空间。首句及长空档只在下一句前 6 秒内显示歌词/提示点，邻近首两句同步预显示。保留提示点 1.5 倍/描边，以及已部署字体。

Release/x64 构建、独立装载、真实 DX11 WARP 渲染检查通过；25%/50%/75% 透明度 RGB 误差最大 1/255；渲染状态恢复检查通过。现有 13685 句时间线检查中 0 句结束后才显影，63 个极短句仍会晚于开唱开始显影。可重复命令：tools\build_ktv_render_regression.cmd。

已在游戏退出时直接替换 DLL 并核验 SHA-256：E4354834933B210133ADC52E710C1EFFF5411F9E5142212358836079E85B64EA。修复前旧 DLL 位于游戏模组 backup/2026-10-11-101838-composite-fade；最终替换另存 backup/2026-10-11-101948-composite-fade-final；验收包位于 artifacts/lyric-composite-fix-delivery/歌词透明过渡修复.zip。BUILD VERIFIED / LOGIC VERIFIED / RENDER VERIFIED / DEPLOYMENT VERIFIED；实际字体画面及游戏听感仍为 IN-GAME VERIFICATION REQUIRED。未改变游戏签名、Hook、逆向字段或 Mod 加载生命周期。

字体与歌词显示修订部署（2026-10-11）：字体库新增 DFP 太丸ゴシック体 SB 与 EPSON 太丸ゴシック体 B；字体列表过滤 DFG POP Mix W5（仅模组列表隐藏，不卸载 Windows 字体）。同时部署歌词提示点 1.5 倍放大/描边、首句前 6 秒提示、0.5 秒淡入、结束后 3 秒再淡出及相邻首两句预显示。统一 DLL SHA-256 922D5AB4F09F001C62B6C371C22A1CA202835276B0677D4D4AF0C2E345E16078 与构建一致；两份字体文件哈希核验通过；旧 DLL 已备份于游戏模组 ackup\\2026-10-11-font-ktv-001017。游戏画面与字体实际观感待用户验收。

KTV 显示微调（2026-10-10）：省略提示保留小圆点样式，圆点直径与间距放大至约 1.5 倍并增加深色描边；首句前仅在开唱前 6 秒内出现圆点。歌词按预告窗口淡入 0.5 秒，结束后保留 3 秒再淡出 0.5 秒；相邻较近时第一、二句可同时预显示。Release/x64 构建通过；游戏画面验收仍待用户确认，未修改逆向 Hook。

全量导出与部署完成（2026-10-10）：用户明确授权后，按当前有效9来源重新生成309首完整SRT/Ruby/审计，无新解包。927份安装文件哈希全通过；最新版界面修复DLL已替换游戏，哈希1377E54A2DB0D3A4AE091FE7146E2E9C13AF320CF78EB2B817AFF7B99FDE1DED；配套工具和Janome依赖已同步，现有配置/字体与OBS密码保持。旧322首经当前文件和原生成来源哈希重核后迁移所有权，回收13份当前未启用DLC来源的旧SRT；原DLL、全部歌词与注音、配置已备份。PV424注音与已验收文件一致。BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED；新面板视觉与PV809注音、音频、真实录像仍由用户游戏验收。98行需读音复核，其中44行58字未确认，见审计。下方暂缓部署记录已由本次授权和部署替代。


振假名流程修复（2026-10-10）：确认游戏仅PV424有Ruby旁路，旧短入口遗漏批量注音。已将最终SRT行序→同源罗马音/Janome→Ruby TSV及审计→三件套哈希安装保护接通；修复长音符空值与送り仮名后缀拆分。309首SRT哈希不变，生成24313个标注；98行待复核，其中44行58字仍缺可靠读音，均有审计。不重新解包。PV809截图句注音已验证，游戏视觉仍需验收。界面右侧跟随布局/中文字形修复已构建并装载通过，DLL为1377E54A2DB0D3A4AE091FE7146E2E9C13AF320CF78EB2B817AFF7B99FDE1DED。用户要求不急部署先查注音，本轮新DLL及注音暂不写游戏，后续统一部署，不让用户自行替换。


PV 工具界面修复（2026-10-10）：窗口跟随 Lyric 右侧并顶部对齐，固定适合文字的宽度与内容自适应高度；补齐工具模块中文字形，修复音频等文字显示问号。BUILD VERIFIED / 独立装载通过；最新 DLL 哈希 1377E54A2DB0D3A4AE091FE7146E2E9C13AF320CF78EB2B817AFF7B99FDE1DED。游戏仍运行，已请求正常退出，待退出后由主编排继续直接部署；视觉 IN-GAME VERIFICATION REQUIRED。


OBS 本机配置（2026-10-10）：已备份 portable global.ini，启用 WebSocket 4455 并保留认证，已有密码同步到游戏 tools/obs-helper.json；已重启空闲 OBS、完成真实认证连接测试并启动后台 Helper。未启动录像；自动录制仍需用户在游戏面板启用并验收。


最新部署（2026-10-10）：用户要求验收版必须直接应用到游戏，此约定已写入 AGENTS.md。主编排已备份并替换游戏 mods/MMFreeLyrics/MMFreeLyrics.dll，同时安装配套工具；部署哈希 E65A0746F285D1DEDD72732EDF51A7DF9381719A47B95F36C2838DC3549DF2D1 与统一构建一致（DEPLOYMENT VERIFIED）。部署时游戏已退出；下一步由用户启动游戏验收新面板、人声开关及 OBS。下方未部署描述属于此前打包阶段记录。


## 三路并行 MVP 交付（2026-10-10）

最终修改、构建与打包统一由主编排负责。已按用户反馈撤回重复的 Ctrl+G 说明，仅保留窗口标题中的快捷键提示；重新构建和独立装载通过，验收包同步更新。

用户明确确认歌词功能已验收完成，隔壁的小修复不阻塞本轮。已授权三个 sub agent 并行实现歌词导出器、Non-Vocal 和 OBS 自动录制，主代理负责接线、构建、整合交付，游戏内 MVP 由用户验收。

用户要求避免重复解包。三路均已确认本轮未进行新 CPK/FARC 解包；复用约定与已核实重复样本见 [EXTRACTED_ASSET_REUSE.md](EXTRACTED_ASSET_REUSE.md)。本轮不删除历史资产副本。
三路 MVP 已完成实现并统一构建：歌词工具两次输出309首/9来源、零失败、SRT哈希一致，少于历史322的13首均属于当前未启用Retro Charts/DLC Songs；安装保护、禁止隐式解包和联接点路径保护已验证。Non-Vocal 声道增益函数唯一签名与92字节语义已审计；OBS七项模拟测试含真实本机管道已通过。最终 DLL 独立装载通过，SHA-256 为 E65A0746F285D1DEDD72732EDF51A7DF9381719A47B95F36C2838DC3549DF2D1。

交付 artifacts/pv-tools-mvp/DivaPvTools-MVP.zip，统一说明见 [PV_TOOLS_MVP_ACCEPTANCE.md](PV_TOOLS_MVP_ACCEPTANCE.md)。状态 BUILD VERIFIED / LOGIC VERIFIED；新音频Hook、声音恢复、真实OBS录像和首尾事件仍为 IN-GAME VERIFICATION REQUIRED，按用户要求自行验收。本轮未部署或启动游戏，未实际录像。完整EXE和智能增量仍是后续项。


## 最新功能规划（2026-10-10）

用户已确认可复用歌词导出器、ImGui 可开关 Non-Vocal、ImGui 可开关 OBS 自动录制。已核查当前代码与外部依据，详细计划见 [PV_TOOLS_PLAN.md](PV_TOOLS_PLAN.md)。本轮仅调查和更新文档，未实施功能、构建部署或启动游戏。

导出工具将复用既有 322 项流水线并简化入口，运行时保留 SRT；Non-Vocal 人声控制点和 OBS 本机录制边界均为 NOT VERIFIED。下一项为工作区内验证导出短入口。DLL 最新加载状态以本文 2026-09-28“加载恢复验收”为准。


## 当前里程碑

KTV 原生数据 M0 — 为一首**原版 MM+ PV**验证 DSC + `pv_db.txt` 能否重建未来日语歌词时间线；这是可靠预显示下一句的当前卡点，正式双栏 KTV 暂不宣称完成。

## 最后已验证状态

已检出 MMFreeLyrics 上游提交 `86ca9825bba1e3c6a84a48d05768de4d57288c18`。当前是 **RECONSTRUCTED BASELINE**，不是原始上游基线：不可访问的私有 `mos9527/srtparser` 已替换为公开固定提交 `38dd4def3eda841d1cb7cf6964a10fd8dbca22f7`，不可访问的 ImGui fork 已替换为 Dear ImGui `v1.88` 固定提交 `9aae45eb4a05a5a1f96be1ef37eb503a12ceb889`。

已确认项目的 Release/x64 配置要求 `PlatformToolset=v142`。本机 Visual Studio Enterprise 2022 现已具备 MSVC `14.29.30133`；重试构建后不再出现 `MSB8020`，证明 v142 工具集可用。

## 工作中

已移除临时硬编码英文 Spike，完成最小 KTV 数据流能力：公开 SRT parser 的结果被复制为项目自有 `LyricLine` 时间线；当前句、下一句提前 3 秒、空白区 `...` 均可从完整时间线计算。由于尚无已核验的正式日语资料，这不代表正式 KTV 已完成。

渲染已改为前景绘制列表：采用两条等权交替轨道，左上轨与右下轨使用相同字号、描边、阴影和透明度；当前演唱轨从左到右填充，另一轨始终显示下一句未填充文本。行结束后下一句保持原轨开始填充，已唱轨承接再下一句。此路径不再依赖不可复现 ImGui fork 的私有字体字段。

最新版本新增原生日文歌词采集，并保留现有 SRT 时间线加载路径。PV424 现已部署由官方 DSC + 文本表生成的原生派生 SRT；当配置尚未保存时默认会尝试加载本地缓存，文件缺失则回退原生当前句。同一版本新增“ワイプ前/后”两套可保存颜色、左右栏坐标、行坐标、预显示时间和从左到右裁剪填充。最新构建将默认视觉改为白字黑边→黄字白边，并新增无需进入 PV 的固定双栏预览。

字体保存重载现仅失效 DX11 后端对象并重建字体图集，不再销毁 ImGui 上下文；此前 imgui_impl_dx11.cpp 的空纹理断言应由此消除（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。空档显示也已改为独立的逐秒圆点区：最右点先淡出，空档内不再绘制文字省略号或提前塞入下一句（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。

离线振假名输入审计已完成：PV424 官方 mdata_pv_db.txt 的 53 条日文歌词均有同编号罗马音，38 条含汉字，且没有缺配对。罗马音没有词或汉字边界，故可用作形态分析读音的校验，不能单独可靠地产生逐字振假名；审计结果见 artifacts/PV424.furigana-input-audit.json（LOGIC VERIFIED）。
用户保存的字体配置曾为 100px 歌词 / 35.5px 界面字体，启动时触发 DX11 字体纹理断言。已备份为游戏模组目录内的 config.before-font-reset.toml，并恢复游明朝 86px / 界面 13px / 描边 4px；代码还将界面字体加载值与滑块上限限制为 24px（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。
已修复模组未加载：字体路径被手工写为 TOML 非法反斜杠，严格解析器会拒绝整份模组配置。现有配置已改为正斜杠并通过严格 TOML 解析；DLL 保存字体路径时也会规范化为正斜杠（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。PV424 Ruby TSV 已生成并部署；DLL 可选载入同名旁路文件并按词组 Ruby 渲染，规格见 FURIGANA_SPEC.md（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。
Ruby 已由用户在 PV424 游戏画面确认可见且正确（IN-GAME VERIFIED）。长空档与普通换句状态机现已改为稳定预告：长空档仅在最后 3000 ms 同时显示圆点与下一句；普通换句的下一句从前一句期间持续到开唱，不再中途隐藏。左右 X 改为单一安全边距镜像，默认上下轨 Y 调整为 0.72/0.88 以避免 Ruby 相撞。新版 DLL 与仅包含上述布局变更的配置已部署，DLL SHA-256 为 E187ED498B16146803EC87D9202277D461BE14383AE61FD74416D7A039083A49（BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。

本机游戏运行时验证目录为 `E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus`。已部署最新版 `MMFreeLyrics.dll`、由 PV424 官方原生时间线生成的 `lyrics\PV424.srt`、`fonts\00-noto-sans-jp.ttf` 与仅本机使用的 `fonts\00-ktv-yumincho-demibold.ttf`。原生歌词事件首次出现时会把其 Unicode 字符加入字体图集并请求重建；这是日文不再显示为 `?` 的必要修复。DLL 与 SRT 均已用 SHA-256 与来源产物核对一致。

该目录的 DivaModLoader 配置使用 `priority` 白名单；已将 `MMFreeLyrics` 放在列表首位。否则 DLL 不会被加载。Chinese Lyrics Mod 的文件与配置未被本项目修改；用户目前已手动关闭该 Mod。

人工游戏内验证已完成：PV 鉴赏画面截图中清楚显示底部居中的两行硬编码文本。截图同时显示原有中文歌词内容，证明 DML 已加载本 DLL，且中文歌词 Mod 未阻塞 Overlay。

## 当前实现

已实现行级 SRT KTV MVP：项目自有时间线、当前句、下一句 3 秒预显示、空白区与描边/阴影双行绘制。测试素材为 `testdata/PV424.ktv-smoke.srt`；它是验证资料，不是 PV424 的正式歌词。

成片规格、字体与排版预设、证据边界及每轮验收循环见 [KTV_SPEC.md](KTV_SPEC.md)。原生首次播放没有可靠的未来行时间，故不能把现有左栏当前句误标为已实现的正式双栏预告。

数据策略已更新为“优先验证 DIVA 原生 DSC + pv_db 时间线；外部 SRT 仅作后备”。当前 hook 的反应式限制不再被视为游戏数据能力的上限。原生数据假设、事实、未证实点、运行时/离线提取器比较与 M0 验证顺序见 [native-lyric-timeline.md](research/native-lyric-timeline.md)。当前没有一首已验证的原生时间线。

用户已使用既有 MM+ CPK 提取能力成功导出原版文本数据库：`E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\diva_main_region\rom_steam_region\rom\pv_db.txt`（**EXTRACTION VERIFIED**）。该成果只证明原版文本资料可读；尚未证明任一 PVID 的 `pv_xxx.lyric.NNN` 完整表、原版 DSC 的 `TIME + LYRIC ID` 或两者映射。当前权威交接与范围见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

随后已以原版 PV276 完成第一条完整关联验证：`pv_276_normal.dsc` 按 Open-PD-Script-Editor 的 Future Tone 读取规则得到 64 个 `LYRIC` 事件，其中 50 个非零 ID 与原版 `pv_276.lyric.001–050` 全部对应，另有 14 个 ID 0 清屏事件。`TIME` 的 10^-5 秒单位亦有两份现成实现/格式资料佐证。详情、文件 SHA-256、样本事件和验证边界见 [pv276-native-lyric-evidence.md](research/pv276-native-lyric-evidence.md)。

用户实际测试的 PV424 属于官方 DLC：已使用既有 FarcPack 从 `diva_dlc00.cpk` 解出 `rom_steam_dlc/rom/script/pv_424_normal.dsc`，SHA-256 为 `8714FD0DB754F2202B2619D921FADB8ABAFC990FB033B6D280E1C1ACC6405461`。`mdata_pv_db.txt` 的 53 条 `pv_424.lyric.NNN` 与该 DSC 的 60 个歌词事件已合成 53 条正时长行：首句 1333–3770 ms、中段 85708–89270 ms、尾句 147770–157533 ms，故 PV424 原生行级时间线为 **LOGIC VERIFIED**。

原生模式的首次播放只能在歌词事件触发后获知当前句；下一句和完整时间边界会随事件持续采集。逐字精确时间尚未取得：首次遇到一行时使用可配置的 4000 ms 整句预估ワイプ，后续相邻事件闭合该行后才可使用实际行时长均匀推进。两者都不代表逐字时间。

同一游戏会话内重播同一 PVID 时，已采集的原生行时间线会保留并去重，可用于下一句预显示与整句ワイプ；跨进程持久化尚未实现。

## 阻塞项

原版数据能否提供未来文本/事件的结构性阻塞已解除（**LOGIC VERIFIED**）。剩余阻塞是：尚未用 PV276 的首句、中段、尾句把 DSC 时间换算与游戏 `currentPlaybackTime` 对齐，也尚未把原版时间线产物接入 Mod。因此正式当前/下一句、3 秒预告和可靠整句时长仍为 **IN-GAME VERIFICATION REQUIRED**。不得猜测二进制 `pv_db`，也不得使用 X Song Pack/F2nd 的明文资料替代本原版验证。

## 验证

构建：**BUILD VERIFIED**（**RECONSTRUCTED BASELINE**）。

已执行的安全基线构建命令（输出重定向到工作区，未写入游戏目录）：

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe' `
  'Source\MMFreeLyrics.sln' `
  /nologo `
  /t:Build `
  /p:Configuration=Release `
  /p:Platform=x64 `
  /p:OutDir='D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\baseline\' `
  /p:BaseIntermediateOutputPath='D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\intermediate\' `
  /v:minimal
```

结果：成功生成 `D:\Work\Projects\VibeCoding\DivaKaraOkeLyrics\artifacts\baseline\MMFreeLyrics.dll`。

逻辑：**LOGIC VERIFIED**（时间线转换、当前/下一句查询、3 秒预显示、空白区选择和 KTV 绘制路径均已编译；SRT 末尾分隔行的 parser 边界已纳入测试资料）。

游戏内：硬编码双行视觉 Spike 为 **IN-GAME VERIFIED**。

日语字体与当前句渲染：**IN-GAME VERIFIED**（PV424，日文、描边和阴影均可见）。

下一句预显示、空白区与第三行 parser 边界：**IN-GAME VERIFICATION REQUIRED**。

原生歌词事件：原版 PV276 的完整离线 `TIME + LYRIC ID → 文本` 数据关联为 **LOGIC VERIFIED**；将其接入运行时后的 next/pre-cue 仍为 **IN-GAME VERIFICATION REQUIRED**。

原生采集、日文字体图集更新和配置化ワイプ：**BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED**。固定双栏预览、游明朝预设与白→黄配色：**BUILD VERIFIED / IN-GAME VERIFICATION REQUIRED**。

自动游戏验证：已用 `DivaMegaMix.exe` 启动测试，但当前电脑操作接口未枚举任何 DIVA 窗口，不能可靠发送按键或获取截图。测试进程已结束；自动化验证为 **NOT AVAILABLE IN CURRENT ENVIRONMENT**，需在窗口接口可用后重试。

## 下一步行动

1. 启动 PV424，以首句、中段、尾句人工核对游戏 `currentPlaybackTime` 与已部署原生派生缓存，并确认右栏在下一句前 3000 ms 出现、当前栏在行结束时退出。通过前不扩展到其他 DLC、全曲、X Song Pack 或新的运行时 hook。

## 恢复点

PV424 官方 DLC 的 DSC 提取和 53 行原生时间线已通过逻辑验证，原生派生 SRT 与 DLL 已部署。恢复工作时先读 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)，只做 PV424 首句、中段、尾句游戏内同步验证及右栏预显示验收。

## 最新交接补充（2026-09-27）

已部署稳定预告 DLL（SHA-256 `E187ED498B16146803EC87D9202277D461BE14383AE61FD74416D7A039083A49`），但用户尚未对长空档、普通换句与镜像边距进行新版游戏内回归。上轨 `Y=0.72` 经用户观察过高，应在下一次部署改为 `Y=0.76`，下轨维持 `Y=0.88`。固定 86px 歌词在 4K 中相对变小的问题已被用户确认；需要实现与窗口高度同步的高分辨率歌词图集重建，不能仅缩放旧图集（未实现）。后续游戏测试须以可见窗口启动。
2026-09-27：歌词分辨率缩放已构建并部署。窗口高度相对 1080p 的倍率会触发安全帧图集重建（0.75–2.00，4K 约 2 倍）；Ruby、描边、阴影与圆点同倍率绘制，ImGui 面板不缩放。为防止大尺寸全日文字集触发纹理断言，图集改为仅构建当前歌词字符集。上轨布局已从 0.72 小幅回调为 0.76，下轨仍为 0.88。部署 DLL SHA-256 为 DA2D16DF69A7B2970ED050AFB4C8DC78E20F045CA5BCDA1249563F7D8B81B10B（BUILD VERIFIED / DEPLOYMENT VERIFIED / IN-GAME VERIFICATION REQUIRED）。

## 单曲缓存泛化准备（2026-09-27）

已审计离线路径：现有提取器只接受一个明确 PVID、已提取 DSC、文本表和 opcode 表，不扫描 CPK、发现曲目或写入游戏目录。新增 `scripts/verify_native_lyric_cache.py` 可校验一对同源 JSON/SRT 缓存；PV424 的 53 行产物已通过逻辑校验。该准备未改变运行时、逆向层或当前仅 PV424 的资料范围。

“覆盖所有 PV”仍需先完成 PV424 三点游戏同步，并由用户明确授权逐曲、按资料包处理；当前不允许全曲扫描、批处理 CPK、通用数据库或新运行时 hook。

## 泛化首批离线缓存（2026-09-27）

用户已确认 PV424 的游戏内同步与双栏效果。已使用同一单曲提取路径生成基础包 PV276：64 个歌词事件生成 50 条正时长行，`artifacts/PV276.json` SHA-256 为 `BCE0E92224E6DF0908F472EF12EA9860361FF5D13DDC276875C6707558B95575`，`artifacts/PV276.native.srt` SHA-256 为 `9E558C6100A74CAB3243BF3424A37D92EA39457BA2CECA841A54EFD385691F20`；缓存一致性校验通过（LOGIC VERIFIED）。PV276 尚未部署或进行独立游戏内三点同步。

泛化策略已开始：基础包和 DLC 均按“显式 PVID、既有工具定向提取 DSC、对应文本表、生成 JSON/SRT、单曲缓存一致性校验”的离线流程推进。不会做 CPK 全盘扫描、通用数据库、运行时新 hook 或写入游戏目录。

## DLC 全量缓存首轮（2026-09-27）

新增 `scripts/build_native_lyric_caches.py`，它发现已提取 rom/script 内的全部 Normal DSC，逐首调用既有单曲提取器和一致性校验器，并写出 JSON 报告。已对 `artifacts/pv424-dlc00-extract` 执行：69 首候选中 60 首成功生成并验证，9 首失败均已记录在 `artifacts/native-caches/dlc00-report.json`。其中 7 首因末尾歌词没有后续事件/清屏而无法取得可信结束时间；PV084 与 PV211 需要进一步处理官方空/多行文本事件。状态：首轮批量缓存为 LOGIC VERIFIED，失败项为 NOT VERIFIED。

## 原生回退关闭与原版对照保留（2026-09-27）

已移除 KTV Overlay 对原生当前歌词事件的时间线回退：没有成功加载 `lyrics/PVxxx.srt` 时，不绘制 KTV 歌词、预告或圆点，避免未缓存 PV 误呈现为已同步。原生歌词渲染 hook 改为始终把游戏传入原文交回原渲染器，故原版歌词可与完整缓存 KTV Overlay 同屏对照。构建产物为 `artifacts/no-native-fallback-build/MMFreeLyrics.dll`，SHA-256 `3A39B3AC457A017A01B9F257EE377FE4D8AA3398AC8D90192875DF9C95BEDF0C`，已部署并与游戏目录产物一致（BUILD VERIFIED / DEPLOYMENT VERIFIED；游戏内回归待验证）。

## 字体预设（2026-09-27）

已载入 `DFG 平成ゴシック体 W5` 与 `DFP 平成丸ゴシック体 W4` 两个本机字体预设。两者为 TTC 集合，渲染器按文件名选择正确集合字形：DFG 使用索引 0，DFP 使用索引 2。默认配置为 DFG；字体目录保留原有游明朝与 Noto 文件。产物 `artifacts/font-presets-build/MMFreeLyrics.dll` SHA-256 `B5DAE353D19FFFAE3627AF9DF028EA57EE655EDB8700B3E73C438045114D1AF3` 已部署并与游戏目录一致（BUILD VERIFIED / DEPLOYMENT VERIFIED）。

## 全资料包缓存与可复用总控（2026-09-27）

用户已授权泛化后，已使用既有 FarcPack 完整解出本机仅有的四个官方 CPK，并建立 `artifacts/installed-native-lyric-sources.json` 资料包清单。基础 `diva_main.cpk` 中发现并成功生成 7 首 Normal DSC 缓存，官方 `diva_dlc00.cpk` 中发现并成功生成 69 首；共 76 首 JSON/SRT 均通过严格同源一致性校验，且已由一键总控部署为运行时 `lyrics/PVxxx.srt` 和 `native-cache-manifest.json`（76 项）。

校验器现保留末句尾随空格，并支持官方空文本及多行 SRT 块；提取器仅对“最后一句没有下一句或清屏”的情形使用同一 DSC 内官方 `PV_END` 时间闭合，普通行仍以紧随的歌词/清屏事件闭合。DLC00 的 PV063、064、084、211、214、223、233、235、236 因此均转为已校验缓存，不使用固定猜测尾时长。

新增 `scripts/build_installed_native_lyric_caches.py`：从资料包清单依次调用既有 FarcPack 总控、读取每包报告并拒绝失败项；仅当所有报告完整成功时才调用部署脚本。后续安装 Mod 时仅需新增清单项即可复用。详细规范和命令见 `docs/NATIVE_CACHE_PIPELINE.md`。状态：**BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED**；游戏内画面回归仍统一保留为 **IN-GAME VERIFICATION REQUIRED**，不作为逐项中间验收。

部署目录收尾：已在游戏退出后清理 65 个早期误复制的 `PV*.native.srt` 重复文件；运行时 `lyrics` 目录现仅保留总控部署的 76 个正式 `PVxxx.srt`，并与 `native-cache-manifest.json` 的 76 项一致。

## 全曲库范围纠正与完整缓存（2026-09-27）

此前将某个子目录扫描到的 76 首误称为完整官方曲目，结论错误，已撤销。正确依据是官方文本表的 `difficulty.normal.0.script_file_name` 映射：基础包声明 178 条（176 条缓存、2 条无 LYRIC 事件），DLC00 声明 71 条（71 条缓存）。批处理现可跨完整解包根目录和区域包按该映射定位 DSC；同一 DSC 映射多个逻辑 PVID 时分别生成，F2nd 的逻辑 PVID 与物理 DSC 编号不同时按 `mod_pv_db` 映射处理。

已纳入当前安装的 X、F、F2nd：X Song Pack 32/32 成功；F2nd Song Pack 38 条缓存、1 条无 LYRIC 事件；F Charts Pack 与 F2nd Charts Pack 的 `script_nc` 是无 LYRIC 的图表脚本，其同 PVID 歌词时序由官方/F2nd Song Pack 的歌曲 DSC 提供，不伪造空缓存。最终按 `官方基础 → DLC00 → F2nd → X` 的显式优先级部署 282 个 `PVxxx.srt`，清单记录 35 项覆盖来源。四资料包一键总控以 `artifacts/installed-native-lyric-sources.json` 复跑通过（BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED）。

`expand_farc_tree.py` 已完成 7,659 个官方基础包 FARC 的单进程展开（零失败）；二级容器没有新增 Normal DSC，证明完整官方脚本路径应以文本表映射跨现有解包分支定位，而不是以单个 `script` 目录或 FARC 计数推断。

## 当前安装 Charts Pack 覆盖收口（2026-09-27）

新增 `audit_chart_lyric_coverage.py`，以各 Charts Pack 的权威 `nc_db.toml` 将物理谱面编号映射到游戏逻辑 PVID，再验证谱面本身不含 `LYRIC` 且逻辑歌曲已有正式 SRT。F2nd Charts 为 **56 覆盖、8 未引用、0 失败**；F Charts 为 **37 覆盖、1 未引用、0 失败**；X Charts 为 **32 覆盖、0 未引用、0 失败**。未引用项只存在孤立 DSC 文件、未由 `nc_db.toml` 注册，游戏不会加载，未伪造缓存。

PV010 是 F2nd Charts 注册歌曲但不在官方 Future Tone Normal 脚本映射中；已从当前安装的 Retro Charts `script_1/pv_010_normal.dsc` 读取 22 行原生 FT `LYRIC`，通过单曲 JSON/SRT 校验后纳入可复用清单。F2nd 的 `PVSC` 特殊 F2 谱面以 68 字节头读取，PV720/PV722 已完整解析且确认无 `LYRIC`。一键总控已从头复跑：官方基础 176 成功/2 无歌词、DLC00 71/0、F2nd Song 38/1、X Song 32/0、PV010 补充 1/0，所有报告 **0 failed**；运行时为 **283** 个正式 SRT、清单同为 283 项，35 项覆盖可追溯（BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED）。画面与节奏仍为 **IN-GAME VERIFICATION REQUIRED**。

## 全部当前安装曲包最终审计（2026-09-27）

扩大检查至当前 `mods` 目录所有含 `mod_pv_db.txt` 的 Mod：Megpoid 6 首、Misaki & Max 2 首、Restore Cut 1 首有歌词（PV027 无文本/无事件）、Retro Charts 30 首有歌词（PV10027 无文本/无事件）、Project mirai 2 Covers Base/F2nd 各 2 首复用歌曲脚本，均已覆盖。Misaki 脚本的 `LYRIC(-1)` 已作为原生清屏事件处理：精确结束上一行、但不作为文本 ID 写入缓存。

最终运行时 `PV*.srt` 和 `native-cache-manifest.json` 均为 **322** 项。对全部当前安装 Mod 的 Normal 注册项进行文本表—缓存对照，所有“有歌词文本”的注册歌曲均存在正式 SRT；所有无缓存项均同时被其文本表和脚本证实为无歌词。状态：**BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED**；视觉和节奏的最终判定仍为 **IN-GAME VERIFICATION REQUIRED**。

## 泛化交付与加载诊断更新（2026-09-28）

全量缓存泛化已完成并保留为可复用总控：scripts/build_installed_native_lyric_caches.py 读取 rtifacts/installed-native-lyric-sources.json，复用既有 FarcPack 解包、逐来源构建、JSON/SRT 同源校验和原子部署。当前运行时已部署 322 个正式 PVxxx.srt，官方基础、DLC00、X、F2nd、Megpoid、Misaki & Max、Restore Cut、Retro Charts 及可复用映射均已审计；无歌词条目不伪造缓存。状态为 **BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED**，画面与节奏回归仍为 **IN-GAME VERIFICATION REQUIRED**。

本轮加载诊断：DivaModLoader 的 dinput8.dll 和其它 DLL Mod 均已进入游戏进程。MMFreeLyrics 同目录、同导出接口的最小探针，在精简元数据下可实际加载，证明目录名和根 priority 正确。旧 config.toml 虽可由严格 TOML 解析，但会被加载器跳过；原配置已备份为 config.toml.before-loader-metadata-fix.toml，当前保留全部 [freelyrics] 设置并使用兼容精简元数据。正式 DLL 在该配置下仍未进入进程。已将 DllMain 字符串分配及 Config 默认值延后至 Init()，最新构建 SHA-256 为 45FF931A649BC4CE18A7BB256204629E3CD06522704986E1541CD8380ADCA5E4，但仍未加载。因此现状为 **BUILD VERIFIED / NOT LOADED IN-GAME**，下一步必须隔离更早的 C++ 静态构造或链接依赖；不得进行 PV 画面验收。每轮测试后均已退出 DivaMegaMix.exe，当前确认游戏进程完全退出。

## 加载恢复验收（2026-09-28）

已定位并修复本轮“MOD 未加载/游戏卡住”的两个独立问题，均与 322 首缓存生成或曲包内容无关：

1. 正式 DLL 的旧式全局初始化会在 DLL 装载期对尚未扫描的 `PvSelector` 签名地址做解引用。独立 `LoadLibraryW` + WinDbg 已在 `MMFreeLyrics+0x1687` 捕获 `c0000005`，对应 `readRelCall16Address(sig...Addr + 0x1D0)`。现已将签名地址、函数指针和 Hook 原始指针延后至 `Init`，并在全部签名确认后绑定。
2. `freelyrics.toml` 的 `author` 行与 `[freelyrics]` 表头曾缺少换行，形成严格 TOML 无效文本；解析失败后启动期 `MessageBox` 会阻塞游戏，造成看似卡死。已备份后修复该换行；代码亦改为配置缺失、损坏或字段不兼容时记录日志并退回默认值，启动期不再弹模态窗口。

加载链路已进行四层实测：最小探针、仅地址绑定、仅 Detours、完整 `Init`。最后一次完整测试的 DLL SHA-256 为 `EF3742FEC55A4B6803F10AF5AEBF72C0F419F35A164F269C98C4F903961BA262`；游戏启动 12 秒后进程存活、`MMFreeLyrics.dll` 位于模块列表，且 `freelyrics-diagnostics.log` 已记录全部 11 个签名、8 个 Hook 及 `config-load`、`lyric-manager-init`、`font-manager-init`、运行时地址读取等所有阶段完成。测试进程已立即结束。

状态：**BUILD VERIFIED / DLL LOAD VERIFIED / DEPLOYMENT VERIFIED**。歌词画面、字体效果、PV276/PV424 时间同步仍为 **IN-GAME VERIFICATION REQUIRED**；不得将本次加载验证误报为歌词显示验收。

振假名异常排查（2026-10-11）：PV049 当前 SRT 与 Ruby TSV 行号一致；游戏目录 TSV 与工作区最终产物 SHA-256 同为 `42274947CB8112387A76130DC3F428A8FC69699D613E42AD2B521BAED123C2C2`，不是旧文件问题。逐项检查该曲19个 Ruby span 后，`飲→の`、`好→す`、`価格→かかく`、`生命→せいめい`、`野菜→やさい` 等均与底字、送り假名及同源罗马音相符；但这还不能解释用户游戏画面所见异常。发现生成器的共性风险：`is_romaji_reading` 以60%序列相似度接纳罗马音，后续逐词分配没有整体读音一致性校验；现有审计仅检查汉字跨度覆盖，不会标记格式合法但疑似错读的 Ruby。因此批量注音仍为 **NOT VERIFIED FOR READING ACCURACY**，需按具体异常歌词行核对并收紧生成与审计规则。本轮只读检查，未改代码、注音文件或游戏目录，未做游戏内验证。

PV049 注音校对稿（2026-10-11）：新增 artifacts/PV049.ruby-review.md，将每个 Ruby 直接附在汉字组后，并列出行号、时间和罗马音来源；原始 SRT/TSV/审计未改动。

可读注音校对工具与 PV253 排查（2026-10-11）：新增 scripts/export_ruby_review.py，支持一个/多个 --pv-id 或 --all，导出逐曲 Markdown、可点击索引，并核对 SRT 时间线、Ruby TSV 与审计一致。已执行全量导出309首至 artifacts/ruby-review-all。确认《LOL -lots of laugh-》为 PV253，现有文件含两处明确错误：ピンク色《ぴんきろ》、世界《せかいらのせかい》。修正了生成器的混合片假名/汉字切分与末尾罗马音粘连；只在隔离目录重新生成 PV253，校对稿显示为 色《いろ》、世界《せかい》。现有全量缓存与游戏目录均未覆盖，未部署；全曲生成器回归和剩余曲目人工校对仍待完成。

PV824「一歩ずつでも」注音错位（2026-10-11）：截图调试信息指向 PV824；当前 sidecar 第 25 行为 `0:1:いっぽ;1:1:ほ`，把单词「一歩」错误切成「一《いっぽ》歩《ほ》」，而同源罗马音为 `ippo zutsu demo`。根因在 Janome 形态词边界与逐 token 罗马音锚点分配：生成器只检查汉字位置均已覆盖，没有校验相邻汉字 span 合读后是否与该复合词罗马音一致，因此没有触发复核提示。正确显示应为「一歩《いっぽ》ずつでも」。本轮定位并记录根因，未修改生成器、缓存或游戏目录；生成规则修复及针对相邻汉字复合词的回归审计仍待处理。

PV824 末句 KTV 提前消失（2026-10-11）：截图时 PV Viewer Time 为 176.32 秒，游戏显示 lyric ID 34。已部署 PV824.srt 与 artifacts/full-export-deployment/cache/PV824.srt SHA-256 一致；文件包含 34 条字幕，最后一句「手に入れるのその声で」时间为 172.401–176.719 秒。截图调试面板却显示外部歌词仅加载 33 条。根因已定位到 Dependencies/srtparser/srtparser.h 的 EOF 处理：它仅在空白分隔行或最后一行读取时 eofbit 已置位才提交字幕；scripts/extract_native_lyric_timeline.py 写出的文件末尾只有一个换行，故解析器漏掉最后 cue。游戏原生歌词走独立事件，所以仍显示。此格式问题可能影响所有使用该解析器读取的、末尾没有空白分隔行的 SRT。本轮只读定位，未改文件、DLL 或游戏目录；需要修复解析器/终止分隔并验证全部 34 条都能加载后，才能进行运行时部署验收。

PV824 末句漏载修复方案（2026-10-11）：最小项目内修复点是 scripts/extract_native_lyric_timeline.py 的 SRT 序列化：末尾由单个换行改为完整空白分隔符（额外一个换行），使当前公开 SubRipParser 在 EOF 前通过空行提交最后 cue；随后必须重新生成并部署受影响的 SRT，PV824 加载数应从 33 回到 34。当前所有原生时间线缓存共用该写入器，因此需全量审计/重生成而不能只补 PV824。长期若要兼容任意手工 SRT，再评估在项目自有加载层修复 EOF flush；无需先改 DLL 或第三方子模块。此处仅记录方案，未执行修改或验证。

PV824 末句漏载修复与全量回归（2026-10-11）：已将 SRT 写入器改为以空白分隔行结束，并在隔离缓存中为 309 首全部补齐终止分隔；使用实际运行时 `SubRipParser` 对全部 309 首逐条解析，末句和非空歌词数均匹配（0 首失败）。扩大检查游戏目录时发现 382 个 SRT 文件中有 73 组未补零旧文件名副本；运行时代码只读取 `PV%03d.srt`，实际启用的 309 首均在修复范围内。安装前哈希预检覆盖 927 个 SRT/Ruby/审计文件，当前无缺失或用户修改冲突。游戏进程仍在运行，部署与最终安装后哈希复验待用户正常退出后执行；状态 **LOGIC VERIFIED / DEPLOYMENT PENDING / IN-GAME VERIFICATION REQUIRED**。

PV096/PV824 注音通用规则修复（2026-10-11）：PV096 `海が近づく` 现生成 `近《ちか》づく`；合并连续纯汉字词后，PV824 `一歩ずつでも` 现生成 `一歩《いっぽ》ずつでも`。对 309 首重新生成 Ruby TSV 与审计文件，并复核 PV253 `色《いろ》`、`世界《せかい》`、`眠《ねむ》ってた` 样本。自动审计仍有需人工复核行，不能据此宣称全部歌曲读音经人工确认。新全量注音缓存和 EOF 修复缓存统一待本机游戏退出后部署。
Ruby 跨空白 cue 错位全量修复（2026-10-11）：运行时 `LoadExternalLyrics` 会跳过空文本 cue，但原 Ruby TSV 使用物理 SRT cue 编号，导致遇到空行后所有后续注音前移/错挂。PV095 在「夢か現か幻」前有空 cue，截图中的「ゆめ・うつつ・まぼろし」因此挂到「ナツばて誘う太陽」；PV049 也有多个空 cue。现已让 Ruby TSV 按运行时保留的有效歌词行编号，审计同时保留原始时间线行号，并更新可读校对工具。309 首全量复生成后，审计行数、Ruby 有效行号、SRT 实际解析数逐曲通过；PV049/PV095 回归校对正确，309 首校对稿导出成功。验证脚本新增空 cue 回归并通过。部署预检 927 个文件无冲突；游戏进程仍运行，等用户正常退出后再部署。
连续短重复歌词全量修复（2026-10-11）：PV255 两处及 PV253/PV246/PV249/PV254/PV262 共发现 10 个连续同 lyric ID、同文本、时间连续且前段不超过 500ms 的重复触发。新增通用合并规则：仅合并这类短片段并保留原始起点/最终终点；较长重复（全量只剩 PV249 一组，首段 3123ms）保留。隔离缓存已合并 10 条，Ruby 重新生成。验证脚本覆盖短重复合并与长重复保留；全量 SRT 解析 309 首零差异，剩余快速重复 0 组，PV255 两处均成单行。修复数据和脚本仍待用户退出游戏后部署。
## 统一歌词与 C++ 修复部署（2026-10-11）

用户完成本轮游戏内排查后，执行一次统一 Release/x64 构建与安装，纳入当前工作树中的歌词段落/切换 C++ 修改及 Non-Vocal、OBS 管理器等已纳入工程的源码；构建成功，SHA-256 为 `88854C99546FF23C7050750F815954D30621321BBBF3D0E822CFFD41D3B4B6BB`。部署至本机 `mods/MMFreeLyrics`：全量 309 首 SRT、309 份 Ruby TSV、309 份 Ruby 审计、5 个歌词工具脚本；已有 Janome 69 个运行库文件保持不变。原 DLL、927 份旧缓存和被替换脚本备份于 `artifacts/deployment-backups/unified-20261011-111449`。73 份旧式未补零 SRT 名称未改动。

部署前证明 927 份目标文件均与上次正式部署来源哈希一致，无手工修改冲突；部署后全部缓存、工具脚本与 DLL 和工作区产物哈希一致。歌词导出回归验证通过；项目实际 SubRipParser 对修复后 309 首 SRT 全量解析，末句及有效行数差异为 0。构建有 C4267/C4244 窄化警告但无错误。状态：**BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED**。本轮未启动游戏；新 DLL 的加载、C++ 伴奏/OBS 等功能、注音画面最终观感仍需用户进入游戏验收，不将安装成功视为游戏内验收。
