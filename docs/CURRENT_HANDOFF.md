# 当前交接：PV424 官方 DLC 时间线

全量导出与部署完成（2026-10-10）：用户明确授权后，按当前有效9来源重新生成309首完整SRT/Ruby/审计，无新解包。927份安装文件哈希全通过；最新版界面修复DLL已替换游戏，哈希1377E54A2DB0D3A4AE091FE7146E2E9C13AF320CF78EB2B817AFF7B99FDE1DED；配套工具和Janome依赖已同步，现有配置/字体与OBS密码保持。旧322首经当前文件和原生成来源哈希重核后迁移所有权，回收13份当前未启用DLC来源的旧SRT；原DLL、全部歌词与注音、配置已备份。PV424注音与已验收文件一致。BUILD VERIFIED / LOGIC VERIFIED / DEPLOYMENT VERIFIED；新面板视觉与PV809注音、音频、真实录像仍由用户游戏验收。98行需读音复核，其中44行58字未确认，见审计。下方暂缓部署记录已由本次授权和部署替代。


振假名流程修复（2026-10-10）：确认游戏仅PV424有Ruby旁路，旧短入口遗漏批量注音。已将最终SRT行序→同源罗马音/Janome→Ruby TSV及审计→三件套哈希安装保护接通；修复长音符空值与送り仮名后缀拆分。309首SRT哈希不变，生成24313个标注；98行待复核，其中44行58字仍缺可靠读音，均有审计。不重新解包。PV809截图句注音已验证，游戏视觉仍需验收。界面右侧跟随布局/中文字形修复已构建并装载通过，DLL为1377E54A2DB0D3A4AE091FE7146E2E9C13AF320CF78EB2B817AFF7B99FDE1DED。用户要求不急部署先查注音，本轮新DLL及注音暂不写游戏，后续统一部署，不让用户自行替换。


最新部署（2026-10-10）：用户要求验收版必须直接应用到游戏，此约定已写入 AGENTS.md。主编排已备份并替换游戏 mods/MMFreeLyrics/MMFreeLyrics.dll，同时安装配套工具；部署哈希 E65A0746F285D1DEDD72732EDF51A7DF9381719A47B95F36C2838DC3549DF2D1 与统一构建一致（DEPLOYMENT VERIFIED）。部署时游戏已退出；下一步由用户启动游戏验收新面板、人声开关及 OBS。下方未部署描述属于此前打包阶段记录。


## 最新实施入口（2026-10-10）

用户确认歌词功能已验收完成，并授权三个 sub agent 并行实现新功能。以 PLAN.md“当前并行任务”为执行入口，最终游戏内 MVP 交给用户验收；不再要求重新验收歌词。

本轮禁止重复全量解包，复用已提取官方资料和 Mod 目录，规则见 EXTRACTED_ASSET_REUSE.md。历史资产副本本轮不清理。三路MVP已统一构建并通过独立装载，交付 artifacts/pv-tools-mvp/DivaPvTools-MVP.zip；下一步由用户按 PV_TOOLS_MVP_ACCEPTANCE.md 验收声音和真实录像，不重新卡歌词验收。


## 最新入口（2026-10-10）

用户已确认歌词导出工具、Non-Vocal 和 OBS 自动录制；本轮仅调查与计划，见 [PV_TOOLS_PLAN.md](PV_TOOLS_PLAN.md)。下一最小任务为 F1-A：复用已有总控整理短入口，工作区输出并校验，不部署游戏。

历史仅 PV424 的限制已被后续授权替代；不自写 CPK 提取器、运行时不解析资产、逆向变更须有证据等边界继续有效。DLL 装载已于 2026-09-28 恢复，见 STATUS.md“加载恢复验收”，本文末尾仍未加载的描述是旧记录。音频控制点和 OBS 本机录制仍未验证。


更新时间：2026-09-27。本文是下一次会话开始后的当前任务入口。

## 目标与卡点

最终产品目标是：在 KTV 渲染时能够在当前句开始前可靠预显示**下一句真实日文歌词**。现有显示 hook 只会在游戏已经显示本句时捕获当前文本，因此不能解决首次播放的下一句预告；必须先取得整首歌未来歌词的原生时间线。

已完成基础包 PV276 与用户实际测试的**官方 DLC PV424** 数据关联：

```text
原版 DSC：TIME + LYRIC ID 序列
原版 pv_db.txt：lyric ID → 日文文本
--------------------------------
结果：{ time, text }[]
```

这证明了资料可行性，但不是完整提取器、全曲处理或正式 KTV 开发。

## 已验证进度

- MMFreeLyrics 是 **RECONSTRUCTED BASELINE**；历史私有 `mos9527/srtparser` 不可访问，不能称为可复现的原始上游基线。
- 重建 DLL 已构建并人工游戏内验证可加载；硬编码双行 Overlay 与原生日文当前句均已有可见证据。
- 原版文本数据库已导出：`E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\diva_main_region\rom_steam_region\rom\pv_db.txt`。这是 **EXTRACTION VERIFIED**；其中单一 PVID 的完整歌词表尚未核验。
- 当前 native display hook 仅提供已触发的当前句；其 4000 ms 估算ワイプ不是正式时间轴，也不能称为下一句预告已完成。
- PV276 的 `pv_276_normal.dsc` 已按 Open-PD-Script-Editor Future Tone 规则完整读取：64 个 `LYRIC` 事件（50 个非零文本 ID、14 个清屏 ID 0）与 `pv_276.lyric.001–050` 一一对应；时间单位为 10^-5 秒。详见 `docs/research/pv276-native-lyric-evidence.md`。
- PV424 不在基础 `pv_db.txt`，但存在于官方 DLC `diva_dlc00_region\rom_steam_region_dlc\rom\mdata_pv_db.txt`：完整歌词键为 `pv_424.lyric.NNN`，数据库同时声明 `rom/script/pv_424_{easy,normal,hard,extreme}.dsc`。已由既有 FarcPack 从 `diva_dlc00.cpk` 解出 Normal DSC；60 个歌词事件与 53 条官方文本对应，已生成并部署 PV424 原生派生时间线缓存。

## 强制顺序

1. 在游戏内播放 PV424，以首句、中段、尾句对照已部署缓存与 `currentPlaybackTime`。
2. 验收右栏在下一句开始前 3000 ms 出现、当前栏在 `end_ms` 退出，长空白区显示 `...`。
3. 三点同步通过后，再将运行时数据源由原生派生 SRT 缓存迁移为 `PV424.json`；不得扩展到其他 PVID、全曲扫描或新的 hook。
4. PV424 已由官方 DSC 与文本表生成 53 条正时长行（首句 1333–3770 ms、中段 85708–89270 ms、尾句 147770–157533 ms），并已部署原生派生 SRT 缓存。当前 DLL 使用左右等权交替轨：第 1 行左上、第 2 行右下、第 3 行左上；演唱行只在所属轨填充，另一轨显示下一句。下一步是在游戏内核对首句、中段、尾句与 `currentPlaybackTime`，并验收该切换。

## 明确边界

- 不自行实现 CPK 提取器，不猜测或逆向二进制 `pv_db`。
- 不把 X Song Pack、F2nd 或其明文 `mod_pv_db` 作为本 M0 的主验证来源；此前相关观察仅是历史探索。
- 原版 `diva_main_region.cpk` 的 `pv_db.txt` 是当前首选输入；DLC 的 `mdata_pv_db.txt` 在首个原版证明完成前不进入范围。
- 不实现通用数据库框架、全曲扫描、运行时新 hook、JSON 缓存或新的 KTV/SRT 行为。
- 现有 `LyricLine` 和渲染层不改动；外部 SRT 仅在原生资料缺失时后备。

## 验收

PV276 与 PV424 的数据关联均为 **LOGIC VERIFIED**。PV424 原生派生缓存与 DLL 已部署；时间和游戏播放时钟的三点同步、正式左/右双栏下一句预显示仍是 **IN-GAME VERIFICATION REQUIRED**，正式 JSON 运行时缓存加载尚未实现。

## 最新视觉交接（2026-09-27，下一会话第一优先级）

用户已在 PV424 游戏画面确认：词组 Ruby（平假名）显示正确，当前字体、描边和基本 KTV ワイプ可以作为已验证基线。当前已部署的 DLL 为 `artifacts/resolution-scale-build/MMFreeLyrics.dll`，SHA-256：`DA2D16DF69A7B2970ED050AFB4C8DC78E20F045CA5BCDA1249563F7D8B81B10B`。

该部署包含以下**尚待游戏内回归验收**的状态机修正：

- 普通相邻换句：下一句从前一句演唱期间持续显示到自己开始演唱，不能闪现、隐藏或替换为下下句。
- 长伴奏空档：空档早期仅显示逐秒圆点；距下一句开始最后 3000 ms 时，圆点保留且下一句稳定出现；不得先提前显示下一句、再隐藏、再显示。
- 水平位置：右轨由 `1 - 左侧安全边距` 镜像计算，不能单独保存成不对称值。

用户确认 `Y=0.72/0.88` 的上下距离过大，现已将游戏配置小幅回调为上轨 `Y=0.76`、下轨 `Y=0.88`（DEPLOYMENT VERIFIED）。仍须用含 Ruby 的真实 PV424 行截图确认不重叠且不过分分离。

### 4K / 分辨率缩放（已构建并部署，待游戏内验证）

现状：歌词使用固定 `fontSize=86` 物理像素；窗口从 1080p 改为 4K 时，歌词在画面中的相对尺寸会变小。用户要求歌词以 1080p 为视觉基准随输出窗口高度同比缩放：4K（2160p）应约为 2 倍视觉字号，且 Ruby、描边、阴影、圆点间距和两条轨道的避让距离必须同比缩放；ImGui 配置面板不需要随之放大。

实现已完成：歌词图集以窗口高度除以 1080 的倍率（限制在 0.75–2.00）于安全帧重建；4K 使用约 2 倍字形，Ruby、描边、阴影及圆点间距随倍率同比绘制，ImGui 配置面板保持原大小。为避免 172px 的完整日文范围造成 DX11 纹理断言，图集只构建当前 SRT/Ruby/已捕获歌词字符；没有歌词字符时仅保留基础字符集，待歌词进入后重建。该实现为 BUILD VERIFIED / DEPLOYMENT VERIFIED，尚需用户可见的 1080p/4K 对比验证；不要隐藏游戏窗口启动。

### 启动约定

此前测试使用的是 PowerShell `Start-Process -WindowStyle Hidden`，这是启动器行为，不是 DIVA 功能。用户明确要求：后续凡由助手启动游戏以测试，必须正常显示窗口，先说明测试目的，便于用户观察和纠正操作。
## 泛化启动更新（2026-09-27）

用户已确认 PV424 的游戏内效果。PV276 已生成并通过 JSON/SRT 一致性校验的 50 行基础包缓存（LOGIC VERIFIED）；后续覆盖以显式 PVID 的单曲离线任务推进，不做 CPK 全盘扫描或新的运行时 hook。PV276 的独立游戏内三点同步仍待后续验收。

## 全量缓存交接补充（2026-09-27）

此前“仅 PV424、不得批处理”的范围已被用户后续明确授权替代。当前可复用总控为 `scripts/build_installed_native_lyric_caches.py`，以 `artifacts/installed-native-lyric-sources.json` 作为本机官方资料包清单。本机游戏根目录只有四个官方 CPK；基础包产生 7 首、DLC00 产生 69 首，共 76 首原生派生缓存已通过 JSON/SRT 审计并部署。没有缓存时，KTV Overlay 保持关闭，游戏原版歌词始终渲染；这条运行时行为不变。

## 当前全曲库交接（2026-09-27）

此前 76 首仅是错误子目录的扫描结果，不代表曲库。当前官方与安装 Mod 的可复用入口是 `artifacts/installed-native-lyric-sources.json` + `scripts/build_installed_native_lyric_caches.py`。当前部署为 282 个逻辑 PVID 的正式 SRT；来源顺序是基础、DLC00、F2nd、X，覆盖项写入运行时 `native-cache-manifest.json`。F/F2nd Charts 的 `script_nc` 无 LYRIC，不应作为歌词时序源；F2nd 依 `mod_pv_db` 的逻辑 PVID→物理 DSC 映射生成。

## 最新加载恢复交接（2026-09-28）

优先级已从歌词效果验收切换为 DLL 装载恢复。已证实：其它 DLL Mod 和最小 MMFreeLyricsProbe.dll 可进入游戏进程；旧历史 config.toml 会被加载器跳过，现已以精简元数据保留 [freelyrics] 设置。正式 DLL 即使延后 DllMain 字符串路径与 Config 默认值初始化仍不能加载；最新测试产物 SHA-256 为 45FF931A649BC4CE18A7BB256204629E3CD06522704986E1541CD8380ADCA5E4。下一步应以最小增量隔离全局静态构造或链接依赖，恢复正式 DLL 进入进程后才做 PV424 或 PV276 的画面测试。所有测试游戏进程均需验证后立即退出。
