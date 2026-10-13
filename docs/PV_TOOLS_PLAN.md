# 三项功能实施计划

更新时间：2026-10-10。用户已确认三项需求，用户随后已授权三路sub agent并行实施；MVP已完成实现、构建与离线验证，游戏内由用户验收。本轮未部署或启动游戏。本计划是最新功能范围，历史验证结论保留。

## 方案核查

| 功能 | 已有依据 | 尚未验证 |
| --- | --- | --- |
| 简短、可复用歌词导出器 | 已有单曲提取、总控、JSON/SRT 同源校验与部署清单；最新记录为 322 项缓存 | 可移植短入口、有效 Mod 优先级发现、增量重建、EXE 打包 |
| Non-Vocal | 社区制作指南描述四声道伴奏/人声布局 | 本机音频内容、人声增益控制点、PV 鉴赏可用性、Mod 曲兼容性 |
| OBS 自动录制 | OBS 28+ 内置 WebSocket；协议提供开始/停止/暂停/恢复/查询录制 | 本机连接、输出暂停支持、可靠 PV 首尾事件及成片边界 |

代码证据：Source/globals.h 定义 PVID、gameModeIndex、isPlaying、currentPlaybackTime。LyricManager::UpdateGameState 以 PV POST PROCESS TASK 开始歌词会话、返回 PVsel 结束，这不是已验证的首帧/末帧事件。LoadSongAudio Hook 只记录文件名，没有音频增益控制。

2026-10-10 核查来源：

- [MikuMikuLibrary](https://github.com/blueskythlikesclouds/MikuMikuLibrary)：FARC Pack 支持 MM+ CPK，继续复用。
- [DivaModLoader](https://github.com/blueskythlikesclouds/DivaModLoader)：priority 首项最高优先级；enabled/include 影响有效来源，不能简单扫描所有 Mod 后以后者覆盖。
- [指南作者的 DivaDocs 草稿](https://docs.divamodarchive.com/User%3ANanase7247/Sandbox)：1/2 为伴奏左右声道，3/4 为人声左右声道。社区说明不能证明全部 Mod 曲都具备独立伴奏。
- [OBS 官方说明](https://obsproject.com/kb/remote-control-guide)与[官方协议](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md)：WebSocket 与录制请求已确认。
- [暂停/恢复竞态报告](https://github.com/obsproject/obs-websocket/issues/1315)：未确认 issue，不能断言所有版本都有该缺陷，仍须本机测试。

## 顺序与实施边界

按用户后续授权，歌词工具、Non-Vocal、OBS三路并行，由主代理集成并交付联合验收包。各项先逻辑、再调试、后可见游戏验证；调查受阻时记录证据，可继续独立的下一项。

### F1：歌词导出器

目标：一个入口完成用户本机资料导出、校验与可选安装。DLL 播放期间不解析 CPK、DSC 或文本表。

1. 整理现有脚本与依赖，新增短入口，只需游戏路径和输出目录；高级来源清单继续支持。工具路径不依赖当前工作目录。
2. 默认只生成 PVxxx.srt、审计 JSON、来源清单和报告；安装为显式操作。保留 Ruby TSV 旁路文件。
3. 按实际 DML 根配置、启用状态和 include 解析来源优先级，追踪逻辑 PVID 到物理 DSC。先支持官方与已验证曲包布局；未知布局和不确定冲突明确报告。
4. 复用现有 FarcPack 与已验证提取逻辑；失败保持旧缓存。用清单区分生成缓存与自定义 SRT，安装时不静默覆盖用户歌词。
5. MVP 通过后加入来源指纹、工具/依赖版本失效检测和增量重建；最后验证 EXE 或带运行环境的可移植工具包。

第一版保留运行时 SRT → LyricLine，不强制迁移 JSON。有效 Mod 覆盖在离线合并时解决，不另建一套竞争的运行时 Mod 来源。DBExtractor.exe 是交付目标，不是已有成果。

验收：任意工作目录与中文/空格路径可运行；重复生成稳定；新增/禁用/调序 Mod 后来源正确；失败不破坏旧缓存；无歌词不伪造缓存；PV276/PV424 同源校验通过。现有 322 项记录不能当作新入口的验证结果。

### F2：Non-Vocal 与 ImGui 开关

1. 单个官方 PV 检查原始音频伴奏/人声分组；优先查现成公开音频实现与 vocal gate/增益调用链，仅调查最小控制点。
2. 核对 PV 鉴赏与节奏模式差异；文件声道号不等于 mixer 输出通道索引。
3. 有充分证据后才新增最小控制：仅人声增益归零，关闭恢复游戏原有控制；不改判定、分数、Combo、整首音量或替换 OGG。
4. 中文 ImGui 新增“仅伴奏”开关，默认关闭，可保存，显示支持/不支持/待验证。优先即时切换；若只能加载时设置则显示“下一首生效”。
5. 验证切换、暂停恢复、重播、换曲和退出后的音量恢复。无独立伴奏的立体声 Mod 曲明确不支持。

验收：仅人声消失、伴奏正常，关闭人声恢复；PV 鉴赏可用；成绩不变；菜单/下一曲正常。地址定位和编译不等于听音验收，通过前标记 IN-GAME VERIFICATION REQUIRED。

### F3：OBS 自动录制与 ImGui 开关

第一版：游戏 DLL → 本机 Named Pipe → 独立 Helper → OBS WebSocket 5.x。认证、网络、超时与重连在 Helper 内；DLL 只发事件、读状态，IPC 非阻塞且有容量限制，游戏帧线程不等待网络。

1. 在已有状态/时钟路径记录加载、播放、暂停、自然结束、返回选曲、重播和换曲，验证生命周期。歌词末句结束不是 PV 结束。
2. 会话 ID 加一次性 Prepared/Started/Paused/Resumed/Ended/Aborted 事件。有效 PVID、目标模式、isPlaying 和时钟前进是开始候选，可能晚于首帧；isPlaying=false 单独不能判结束。
3. Helper 先做连接测试、认证、可用请求检查、GetRecordStatus 与 Start/Stop。默认 127.0.0.1:4455 可编辑，密码遮罩、不记日志；场景和编码输出由 OBS 配置。
4. 自动化 MVP 限 PV 鉴赏，默认关闭；一首一个文件，自然结束/主动退出时 Stop。中文 ImGui 提供“OBS 联动”“自动录制 PV”、连接测试、连接/录制状态、错误和保存。
5. 记录录制所有权：已有手动录制不接管、不暂停、不停止。断线/响应丢失时查询状态并核对会话，所有权不明提示人工处理，不盲目重发。关闭开关时仅收尾本功能拥有的录制；Helper 用心跳识别游戏异常退出并收尾自己的录制。
6. 基础链条稳定后实验 Start → 确认活动 → Pause → 确认暂停 → Resume → Stop。检查录制输出暂停支持，处理取消、超时和失败；保留普通 Start/Stop 模式。
7. 实测成片首尾、音画同步和菜单残留，再加可行偏移。负开始偏移必须有提前事件，收到 Started 后不能补录过去。Start 到 Pause 可能写入菜单，Resume 仍有延迟；预热不保证零剪辑或逐帧准确。

验收：先模拟去重、暂停/结束区分、取消和重播；再实测认证错误、OBS 未启动、断线、已有手动录制、暂停不支持和游戏异常退出；最后可见游戏录制自然结束、中途退出、连续两首。确认文件独立可播放，记录首尾误差。

## 联合交付

- Config 持久化沿用现有路径，音频与录制开关独立；新增方法中文注释，源码 UTF-8，新增界面和日志中文。
- 同时开启 KTV、仅伴奏、OBS，验证音画/歌词同步、帧率、1080p/4K；全部关闭验证基线。
- 签名、偏移、装载生命周期或新 Hook 的变更必须有具体证据、必要性和回退路径。
- 逐项记录 LOGIC VERIFIED、BUILD VERIFIED、IN-GAME VERIFIED；未验收明确 NOT VERIFIED 或 IN-GAME VERIFICATION REQUIRED。

## 下一项最小任务

三路MVP已完成离线验证与构建，下一项是用户按 PV_TOOLS_MVP_ACCEPTANCE.md 验收新工具、声音开关和OBS录像。歌词功能已验收，不作为前置门槛。EXE、智能增量和预热录制仍是后续增强。
