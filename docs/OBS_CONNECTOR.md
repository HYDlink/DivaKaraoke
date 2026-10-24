# OBS 连接器

## 单曲播完仍录制：修复与验收（2026-10-18）

现场PV805《ロストワンの号哭》在218.339秒进入GameResultTask，播放时间冻结，但isPlaying仍为1。旧版本未把该状态视为结束，所以OBS继续录下结束画面，返回PVsel才停止；播放列表因存在切歌事件而绕开问题。不能只按isPlaying或时钟停顿判断自然结束，否则中途暂停也会被错误切文件。

修复：每次进入GameResultTask将当前会话标记为非活跃并撤销准备，Helper沿用StopRecord、确认outputPath、恢复文件名模板和持续待命流程。即使结果画面仍报告播放中或时钟略有残留递增，也不会重启录制。同曲重播在新准备事件后建立新会话。人工暂停仍录在同一文件。

结束通知复用既有ChangeGameState Hook，在原游戏状态切换函数之前发布；准备事件仍在之后读取正确曲名。后台条件变量替代40毫秒固定轮询，变化立即唤醒，每秒心跳保留，不在游戏线程等待OBS。只停止Helper已认领的自动录制，人工录像的所有权边界保持。

验证：真实生产ObsManager回放现场状态与时钟、结束后600帧、重复结果通知、残留时钟、同曲重播、下一首与手动暂停通过；13项Helper模拟、歌词/歌手回归、Release/x64和独立DLL装载通过。产物/证据artifacts/obs-single-end，DLL SHA-256：9FD8A1F547259A7A1A59D96BB2591FE8ED08927395A438C0A05A94DEFB8F05CB。BUILD / LOGIC VERIFIED；真实游戏单曲结束与尾帧仍待验收。

验收无需创建播放列表：开启自动录制，普通单曲播放到结尾，停留在结束画面，确认OBS自动停止并保存一个独立文件，Helper显示已保存后继续待命；重播得到新序号文件。另在曲中手动暂停/继续，确认保持同一文件。

此修复属于结果状态触发的异步停止，不保证结束画面零帧出现。此前可靠PV_END减可调提前量的预测方案仍未实现；其中后台即时唤醒部分已在本轮完成。如后续仍有短暂尾帧，需按新录像与日志单独验证提前量，不能用末句歌词或冻结时钟猜整段PV终点。
更新时间：2026-10-18。本文件是 OBS 功能的独立开发、故障排查与验收入口；STATUS.md 和 PLAN.md 保留摘要。

## 日常启动与连接故障

2026-10-12已修复启动器乱码和闪退：CMD文件使用UTF-8无BOM与CRLF换行，不能用LF或混合换行。失败时会保留中文原因并暂停，正常启动后Python持续运行，窗口显示“OBS Helper已启动”。已通过真实CMD及实际安装入口验证并直接部署；可以自行双击原安装入口，无需Agent执行Python。Git换行规则已加入 `.gitattributes`；编辑后仍需检查实际字节。


本机唯一日常入口：

`E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods\MMFreeLyrics\tools\start_obs_helper.cmd`

先打开 OBS，再双击该启动器，保持启动后的控制台窗口打开（可以最小化），随后在游戏 PV 工具面板点“测试 OBS 连接”。Helper持续运行时，游戏重启后可以再次连接；电脑重启或关闭Helper后需要重新启动。目前没有开机/游戏启动时自动运行Helper的机制。

不要从 `artifacts/pv-tools-mvp/package` 或 `artifacts/obs-playlist-delivery/package` 启动日常Helper。项目内3份同名启动器属于源码和两个发布快照，旧MVP Helper只支持v1，当前游戏使用v2；发布快照和源码未包含本机私有 `obs-helper.json`，日常配置保存在实际安装目录。

连接失败时依次检查：

1. OBS与Helper是否都运行；“Helper未连接”优先检查Helper本机管道，“OBS连接失败”再检查OBS WebSocket服务及配置。
2. Helper已在运行时先点游戏“测试 OBS 连接”，避免反复多开。
3. 需要重启可见控制台Helper时，在其窗口按Ctrl+C，待退出后关闭窗口，再双击上述启动器；重启会收尾其拥有的录制，正在录视频时不要操作。
4. 助手启动Helper须在正常用户环境中进行。2026-10-11已证实工具隔离环境内创建的管道会拒绝真实游戏访问；正常用户环境重启后用户确认连接成功。不能仅以进程存在或独立OBS认证成功宣称游戏已连接，不需要因此重启游戏或改OBS密码。

当前启动器缺少单实例状态检查和一键重启功能，后续整理计划见PLAN.md。冗余审计清单见 `artifacts/tooling-audit/inventory.json`；此次未删除发布快照或备份。


## 当前功能

在 PV 工具面板开启“启用 OBS 联动”和“PV / 播放列表自动录制（持续待命）”。每首单独启动、停止并保存，然后持续待命，无需逐首重开。游戏负责播放列表选曲和切歌。

标题来自已存在的游戏等待画面数据 PVWaitScreenInfo->Name，使用实际生效的曲名，不重新解析 pv_db。无标题时使用 PVID 后备。

- `恋愛裁判-On Vocal.mkv`
- `愛Dee-Off Vocal.mkv`
- `愛Dee-Off Vocal (2).mkv`

后缀在录制启动时固定：现有 NonVocalManager 成功绑定歌曲、启用静音且实际已应用时为 Off Vocal，否则为 On Vocal。文件名格式为 `%s-On Vocal` / `%s-Off Vocal`，其中 `%s` 为实际曲名，便于上传分 P 时删除歌曲名前缀。后缀表示模组静音状态，不能证明社区歌曲混音里完全没有人声。角色/歌手仍由游戏选择，不推测新字段。录制中修改静音不会重命名已有文件，应在每首开始前确定模式。2026-10-11 验证记录中的方括号文件名属于旧格式历史证据。

输出目录、容器、编码器、音轨、场景和自动转封装沿用 OBS 现有配置。本次没有增加 SplitRecordFile、预热、审核热键、播放列表 UI 或自动选曲。

## 生命周期和边界

纯观察模型在 Source/managers/obs_session.h，观察现有信号，不新增签名或游戏 Hook。

1. PV POST PROCESS TASK 建立准备会话；时钟有效、isPlaying 为真且开始递增后录制，保留原启动时机。
2. PV_WATCH、PV_STAGE、PVsel、MAINMENU_SWITCH、MENU、STARTUP 结束旧会话；暂停菜单不结束录制。
3. 已有 _LoadSongAudio 成功加载歌曲时通知 OBS，结束旧会话，补齐不经过 PVsel 的切歌/循环。若没有新准备事件，必须先看到 0–1 秒范围的播放时钟再等递增，避免残留旧时钟误启动。
4. 准备会话内 PVID 变化，或已播放超过 2 秒后在播放中回到 0–1 秒，建立新会话。暂停不根据时钟回退分割；主动跳回曲首按重播新建文件。
5. isPlaying=false 或时钟停住不能单独判断结束，会与暂停混淆；不使用最后一句歌词当 PV 结束。真实播放列表及最后一首自然结束状态序列仍需实测。

游戏帧只发布有界快照；后台 Named Pipe 和 Python Helper 负责网络与日志。v2 快照加入 UTF-8 曲名的十六进制编码及实际静音状态，保留原管道名。新 Helper 兼容 v1，旧 DLL 标题使用 PVID 后备；旧 Helper 不支持 v2，部署须同步更新。

## OBS 流程与安全恢复

检查空闲 → 查询输出目录和原模板 → 持久化恢复记录 → SetProfileParameter(Output, FilenameFormatting) → 再检查空闲 → StartRecord → StopRecord → outputPath → 等输出完全停止 → 恢复模板 → 继续待命。

实测 StopRecord 返回路径后仍有数百毫秒封装收尾，因此 Helper 最多等待 15 秒直到 GetRecordStatus.outputActive=false，再启动下一首，等待只在后台。IPC 在耗时请求中可能暂时提示超时，重复快照不重复启动。

只认领成功 StartRecord 响应。人工录制、人工停止后重启、断联重连、启动响应丢失都不猜测所有权；同一会话不重试。关闭联动/自动录制、退出、下一首、心跳超八秒、Helper 正常退出均尽力停止自己拥有的录制。

非法字符、控制字符替换为下划线；百分号替换成全角，防止 OBS 日期模板展开。曲名最多 100 个 UTF-16 单位，处理空标题、首尾点/空格和 Windows 保留名。同名检查所有扩展名并忽略大小写，加 (2)、(3) 序号，也保留进程内已使用名。

obs-filename-recovery.json 在改模板前保存原 profile 和模板，正常恢复后删除。异常退出后重连继续恢复，仅在原 profile 且模板仍为本功能临时值时回写；用户手改模板不覆盖。切换 profile 时等待回原配置，期间不启动新录制。密码不进入快照、日志或恢复文件。

## 配置和日志

- 模组 obs-tools.toml：enabled、auto_record_pv；默认关闭。
- tools/obs-helper.json：本机地址、端口、密码；部署保留，不入包。
- 模组 obs-runtime.log：状态、歌曲加载、边界和每秒采样，含 PVID、gameModeIndex、GameState、currentPlaybackTime、isPlaying、会话、标题及静音状态。
- tools/obs-recordings.log：开始记录与实际 outputPath。

## 验证记录

- LOGIC VERIFIED：13 项 Helper 模拟测试，包括两首、日文标题、后缀、同名/跨扩展名、非法字符、失败、恢复、人工所有权、丢响应、断联、看门狗、封装等待、真实 Windows 管道 v2/v1。
- LOGIC VERIFIED：C++ 回归覆盖不同曲连续、同曲循环、无重复准备事件、旧时钟保护、时钟重置、暂停和退出，不代表真实游戏事件序列。
- BUILD VERIFIED：Release/x64 和独立 DLL 装载通过，构建在 artifacts/obs-playlist-build。
- OBS VERIFIED：2026-10-11，用户已打开的 OBS 30.1.2 / WebSocket 5.4.2，合成两首会话各录约两秒，确认两份非空 MKV、日文文件名/后缀和原模板恢复。
- 实测文件：D:/Video/OBS连接器验证-20261011-112057-恋愛裁判 [On Vocal].mkv 与 D:/Video/OBS连接器验证-20261011-112057-愛Dee [Non Vocal].mkv，停止时均 30400 字节。这是接口测试，未播放真实 PV。
- IN-GAME VERIFICATION REQUIRED：真实播放列表、同曲循环、最后一首自然结束、首尾帧和音画同步。

## 游戏验收

1. OBS 打开，Helper 后台就绪；游戏 PV 工具面板测试连接，开启联动和持续待命。
2. 建立两首不同曲、非循环 PV 播放列表，预先设定静音模式，连续播放，不逐首重开录制。
3. 确认两份按真实曲名命名的视频；最后一首结束 OBS 停止，模板恢复。
4. 测试同曲重播、暂停恢复、提前退出；暂停保持文件，重播加序号。
5. 合并文件、缺开头或末曲不停时保留 obs-runtime.log 和 obs-recordings.log，据真实边界修正。

## 重复执行命令

从项目根目录运行。多参数按要求以反斜杠分行；PowerShell 执行时将行末反斜杠换成反引号，或合并成一行。

```text
python scripts/test_obs_helper.py

tools\build_obs_session_regression.cmd

python scripts/verify_obs_recording.py \
  --config "E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/tools/obs-helper.json"

python scripts/verify_obs_recording.py \
  --config "E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/tools/obs-helper.json" \
  --record

python tools/obs_helper.py
```

验证脚本不带 --record 时只读检查；带 --record 创建两段测试录像，OBS 正在录制时退出。

## 官方依据

[obs-websocket 官方协议](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md)：GetProfileParameter / SetProfileParameter、GetRecordDirectory、StartRecord / StopRecord、RecordStateChanged。SplitRecordFile 从 5.5.0 提供，本机 5.4.2 没有该接口，本版用 Stop/Start。

部署（2026-10-11）：游戏退出后统一 DLL、Helper 与 35 个依赖文件已直接安装并核验 SHA-256。备份为游戏模组 backup/2026-10-11-112522-obs-playlist；配置、密码、字体和歌词缓存保留。DLL SHA-256：83E4B997E2696694A1C3D0689A1B0A156D37CBCF7ACFC78F448C4EB1A21A618B。后台 Helper 的真实管道和 OBS 认证通过。IN-GAME VERIFICATION REQUIRED。

## PV249 录像尾部加载闪帧调查（2026-10-11）

用户样本：F:/DivaRecord/アゲアゲアゲイン [On Vocal] (2).mkv。只读分析原文件，未修改录像、配置或 DLL。

录像为 HEVC / AAC、60 fps，总长 224.150 秒。末半秒逐帧联系图显示最后 4 帧为下一首加载画面，约 66.7 ms；末两秒黑场检测为局部 0–1.933 秒，加载画面从约文件 224.083 秒出现。末三秒音频在 -50 dB 检测阈值下约前 2.9355 秒为静音。采样和检测存在一帧及音频编码延迟精度边界，不以文件总时长等同游戏时钟。

游戏日志显示 PV249 时钟到 223.018 秒后不再增长，isPlaying 仍为 1、录制仍活跃。待 PVID 变为 PV253 时旧会话才结束，随后进入 PV_STAGE。现有停止信号来自切到下一首，属于反应式边界，加载画面可能已经开始。OBS 停止封装完成的日志时间比 StopRecord 返回路径晚约一秒；封装等待本身不意味着继续采集同样长的视频。

复用已提取官方 pv_249_normal.dsc 和既有 extract_native_lyric_timeline.read_lyric_events，不新解包、不新建 DSC parser：PV_END 为 22300000 原始时间单位，即 223.000 秒，与游戏停钟 223.018 秒一致。脚本 SHA-256：12160DB3AD7CE45321B04C6EA6C5992A979099E422AA655AAE752E68DD7B7FAC。最后歌词结束仅 202.577 秒，不能作为整段 PV 结束。

最小优化方案（DESIGN VERIFIED / NOT IMPLEMENTED）：

1. 从已有离线原生资料保留独立 PV_END 元数据，不修改歌词时间线；有明确结束点时按游戏时钟触发。
2. 新增可调整的 stop_lead_ms，建议从 200 ms 开始，范围可先设 0–500 ms。PV249 的试验触发点为 222.800 秒。逐曲游戏同步仍需验收，其他曲目不能根据此样本猜结束时间。
3. 在会话中记录已自然停止标记，防止末尾时钟不动又重新启动；暂停不推进预计结束时间，重播/循环的新会话重新解锁。
4. 快照变化唤醒后台 IPC，减少现有最多约 40 ms 的轮询等待；已有状态 Hook 的退出通知可在原状态切换前发送，但不能替代可靠终点预测。
5. 无可靠 PV_END 时保留状态/PVID 结束后备，不以末句歌词或“时钟暂时停止”推断自然结束。
6. 用同一首重录验证尾奏/画面未截断、加载帧消失，再测两首连续播放和暂停/重播。

分析产物位于 artifacts/obs-tail-analysis：视频信息.json、末两秒联系图.jpg、末半秒逐帧联系图.jpg、黑场检测.log、尾部音频检测.log。当前游戏仍运行，因此本轮仅调查并记录方案，没有替换 DLL 或重启 Helper。

## 播放列表歌词串曲配套修复（2026-10-11）

OBS 已识别连续切歌，但旧歌词层依赖 PVsel 清理，因此下一首可能仍渲染前曲。歌词管理器现改为每次 PV POST PROCESS TASK 重载 SRT/Ruby，并通过 loadedPvid 和加载状态清理防止串曲。OBS 文件命名、开始/停止时机和 Helper 保持原行为。生产歌词管理器的连续两首、循环、暂停及缺失文件回归通过，修复 DLL 已直接部署并核验哈希；真实游戏两首切歌与振假名仍待用户验收。详情见 STATUS.md 与 ARCHITECTURE.md 的播放列表歌词条目。提前 200 ms 收尾方案尚未实现。