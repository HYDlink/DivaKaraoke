> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# PV261 换句卡顿性能调查

## 目标与证据边界

用户报告PV261《君の体温》每次换句卡顿，关闭Show Lyrics仍卡，停用整个Mod重启后不再卡顿。目标是开启歌词、注音和录制时流畅；关闭显示仅为定位对照。

旧_CopyCharsByCount → SetLyricLine → CaptureNativeLyric → UpdateCharset没有showLyrics守卫。每条新原生句即使没有新增字符仍输出三条LOG，每条三次同步WriteConsoleW，合计至少九次控制台写。新增字符还会使下一帧重读字体、重建整套图集及DX11后端对象。

正式KTV只用整首SRT/Ruby，原生采集数据不参与显示。SRT/Ruby/歌手旁路只在进曲时读取，未发现逐句解析文件或运行时解析DSC。完整缓存预热后不应每句新增字形，因此不能断言所有换句卡顿都由字体重建造成；控制台阻塞的实际毫秒数也尚无现场调用栈证明。

## 已实施修复

- 移除无消费者的原生逐句采集、PVDB收集和对应两个旧Hook；保留原版歌词开关、歌词索引、音频与生命周期。
- 字形由整首SRT/Ruby预热，删除字符枚举同步日志。
- 缓存曲内轨道与行几何；字体版本、输出尺寸、字号、装饰、安全区、轨道及背景改变时失效，切歌清理。
- Ruby直接遍历UTF-8并使用栈缓冲，去除逐帧逐字编码及字符串分配，保持测量和间距。
- OBS只在协议字段变化时编码发布，保留后台心跳、会话边界及录制协议。
- 音频面板只用短锁取状态和提交开关，UI与配置文件写入放到锁外。
- 透明合成资源在D3D初始化及分辨率准备阶段预热，避免首句淡入时编译shader。描边与透明混合规则保持。

## 工具与验证

普通权限WPR报0xc5585011。tools/record_mod_performance.ps1通过独立管理员进程请求UAC，组合GeneralProfile、GPU与diva_performance.wprp；不修改系统策略，不以管理员启动Codex，不取消未知记录。工具自检的实际结果以status.json和ETL实物为准。

修复版提供按需启用的ETW区间：帧总耗时、歌词状态、音频、OBS、字体、图集上传、歌词/注音、面板、DX11提交及透明合成，并标记歌词索引、PVID、播放秒数和显示开关。未启用时不计时、不分配、不落盘。

应在WPA或PerfView中选取真实单次卡顿区间，同时检查CPU采样栈与线程等待。普通CPU火焰图不能单独解释锁等待或驱动阻塞。Mod提供匹配Release优化版PDB；无游戏私有符号时本体可能仅显示偏移。

官方签名PerfView保存在artifacts/performance-investigation/tools/PerfView.exe，下载自微软GitHub且签名有效。UserCommand SaveCPUStacks可导出DivaMegaMix进程原始CPU栈；SaveCPUStacksAsCsv可导出热点表。原始ETL必须保留。

tools/lyric_performance_replay.vcxproj使用真实安装字体、配置和PV261的38句SRT/Ruby，在硬件DX11离屏回放1080p/4K及显示开/关，两个版本顺序运行避免互抢GPU。每帧在计时外等待GPU完成，只读游戏目录。该测量不包括游戏负载、Present、真实控制台阻塞或OBS编码，不能当作游戏帧时间验收。

baseline-replay/frames.csv、fixed-replay/frames.csv记录CPU、字体、绘制、提交和顶点数。8张同一时刻1080p/4K原始RGBA逐字节比较。时间线、缓存失效、字体版本、字号/倍率/安全区/轨道/背景、OBS快照及既有DX11渲染均有回归。具体结果见artifacts/performance-investigation/validation.json。

## 操作

管理员采集入口：tools/record_mod_performance.ps1 -Name pv261-fixed -DurationSeconds 90。

确认UAC后播放PV261，保持Show Lyrics开启并经过多次换句。在结果目录创建pv261-fixed.stop可提前保存；默认90秒上限。对照场景使用不同名称，避免覆盖。当前部署保留config.toml的停用状态，复测前需要重新启用Mod并重启游戏。

修改前源码、原DLL、带PDB基线构建均在artifacts/performance-investigation/baseline-*。只有真实游戏ETL和录制复测通过才能标记卡顿解决；目前未声称取得PV261现场栈、游戏火焰图或完成录制验收。


## 用户实机验收（2026-10-16）

用户部署后反馈：明显好转、没有卡顿，160 FPS也正常。当前复测场景的游戏换句流畅度标记IN-GAME VERIFIED（用户确认）。暂不继续性能采集；真实函数级根因、其他曲目/分辨率及录像成片未因此自动获得验证。
