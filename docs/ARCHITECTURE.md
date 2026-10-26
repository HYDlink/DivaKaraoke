# v0.2.0发布命名（2026-10-26）

当前正式产物为DivaKaraoke.dll，安装目录mods/DivaKaraoke，工程Source/DivaKaraoke.sln与DivaKaraoke.vcxproj。freelyrics.toml保留以兼容用户设置；下文MMFreeLyrics是原第二阶段架构记录。游戏签名、结构体、Hook和生命周期不因更名改变。

# 当前架构

## 上游基线

本项目基于 MMFreeLyrics 提交 `86ca9825bba1e3c6a84a48d05768de4d57288c18`。

## 运行时流程

```text
DivaModLoader
  → MMFreeLyrics DLL（D3DInit / Init / OnFrame）
    → 游戏签名扫描与 Detours hooks
      → PVID、PV 生命周期、播放状态与播放时间
        → LyricManager
          → 项目自有 LyricLine 时间线
            → KTV 显示状态（当前句 / 下一句 / 空白区）
              → ImGui 前景绘制列表
                → DX11 绘制
```

当 DivaModLoader 根配置包含 `priority` 时，`MMFreeLyrics` 必须出现在该数组中；本机验证将其置于首位。该项是加载条件，不是歌词内容的渲染优先级。

## 重要模块

- `Source/mod.cpp`：DivaModLoader 导出、游戏 hooks、DX11/ImGui 帧入口。
- `Source/globals.h`：逆向得到的游戏结构体；包含 `PvSelector::PVID` 与 `DivaPlaybackStatus::currentPlaybackTime`。
- `Source/managers/lyric_manager.*`：外部 SRT 加载、歌词状态、当前行选择、PV 生命周期与歌词 Overlay。
- `Source/managers/font_manager.*`：FreeType 字体图集、填充、描边、阴影与字体 UI。
- `Source/utils/config.*`：持久化配置。

## 当前歌词数据流

```text
待验证正式目标：原版 PVID → 原版 DSC 时间/歌词事件 + 原版 `pv_db.txt` 歌词文本
             → `LyricLine` → 完整行级 KTV 时间线
             → 当前句 / 下一句 / 空白区 / 整句ワイプ

后备路径：外部 `lyrics/PV###.srt` → SubtitleParser → `LyricLine`。

降级显示：游戏原生歌词 hook → 当前日文文本 / 歌词索引 → 仅当前句显示。
```

重建基线使用公开 `simple-yet-powerful-srt-subtitle-parser-cpp` 的固定提交 `38dd4def3eda841d1cb7cf6964a10fd8dbca22f7`。公开 parser 缺少私有 fork 的静态时间戳帮助函数，`LyricManager` 直接以 `SubtitleItem::getStartTime()`、`getEndTime()` 和 `getText()` 选择当前行。

项目不再使用临时英文 Spike；该 Spike 的历史游戏内验证仍可证明 DLL、hook、D3D/ImGui 与模组加载链路可用。当前代码采集原生当前歌词，作为降级显示；其反应式特性不等于底层 PV 数据没有未来信息。原版 PV276 已证明 DSC + `pv_db.txt` 能得到完整未来行序列（见 `docs/research/pv276-native-lyric-evidence.md`），但尚未接入运行时；在其离线 JSON 与游戏三点同步验证完成前，不调整运行时默认选择或增加新的逆向 hook。SRT 仍保留为后备。

KTV Overlay 使用完整 SRT 时间线；每句按独立显示窗口及段落内的左右交替轨道绘制，不以当前句指针变化立即替换旧句。首句与长空档在下一句前 6 秒进入预显示；短间隔前后两句可以同时预显示。普通歌词结束后保留 1500 ms，再淡出 500 ms，同轨后句等待淡出结束并淡入 500 ms；密集短句按同轨可用时间缩短旧句停留，极短句仍可能稍晚开始显影。ワイプ进度在结束后钳制为 1，Ruby 与主歌词保持已唱颜色。已唱/未唱色通过互不重叠的裁剪绘制。半透明时用可复用、随视口尺寸重建的 DX11 透明纹理合成整行，再将预乘颜色和 alpha 一起缩放后混合回原目标；背景、描边、阴影、Ruby 共用整体透明度，避免多次黑色描边的 alpha 累积。合成回调恢复渲染目标、PS 常量缓冲及纹理绑定，再复用 ImGui ResetRenderState 恢复其余状态。整行不透明时沿用直接绘制。提示点在所有空档的最后六秒逐秒收拢，保留 1.5 倍大小及描边。相关纯时间计算位于 Source/managers/ktv_timing.h，合成资源位于 ktv_composite.h；字体仍由既有 FreeType 图集管理。

公开 parser 不提供 `isLoaded`，因此当前实现仅在 SRT 文件存在时尝试解析；解析后以项目自有时间线运行。该行为是重建基线的明确适配，不声称重现不可访问私有 fork 的加载状态语义。

## 重建 SRT parser API 兼容性

| 原 MMFreeLyrics 使用 | 公开 parser 对应项 | 兼容性 | 所需适配 |
| --- | --- | --- | --- |
| `SubtitleParserFactory` | `SubtitleParserFactory` | 是 | 无。 |
| `getParser()` | `getParser()` | 是 | 无。 |
| `getSubtitles()` | `getSubtitles()` | 是 | 无。 |
| `parser->isLoaded` | 无 | 否 | 使用文件存在性检查；不伪造私有 parser 的加载状态。 |
| `SubtitleItem::getByTimestamp(...)` | 无 | 否 | 由项目以 `getStartTime()` / `getEndTime()` 显式选择当前行。 |
| `getText()` | `getText() const` | 是 | 无。 |
| `getStartTime()` | `getStartTime() const` | 是 | 用于构建 `LyricLine::startMs`。 |
| `getEndTime()` | `getEndTime() const` | 是 | 用于构建 `LyricLine::endMs`。 |

第三方许可证通知保存在仓库根目录 `THIRD_PARTY_NOTICES.md`，发布 ZIP 配置也会包含该文件。

## 时间源

当前同步时间为 `playbackStatus->currentPlaybackTime`，在代码中按秒读取，并转换为毫秒用于 SRT 时间戳查询。它来自游戏播放状态，不依赖帧累计时间。

原生事件只在当前行到达时提供文本；未获得下一事件前，该行没有可信结束时间。此状态下渲染器只采用配置的整句预估时长（默认 4000 ms）做视觉ワイプ，不能推断或伪造逐字时间。

## 原版资料验证边界

当前首选资料是已从 `diva_main_region.cpk` 导出的 `rom_steam_region/rom/pv_db.txt`。M0 必须先证明单一原版 PVID 的 `pv_xxx.lyric.NNN` 与同一原版 DSC 中 `TIME + LYRIC ID` 可以连接为数行 `{time, text}`；这将让运行时在本句开始前已知下一句，从而解除 KTV 预显示的核心限制。

该阶段使用已有 MikuMikuLibrary/FARC Pack CPK 提取能力及 Open-PD-Script-Editor 的 DSC 解析作为资料工具，不在 Mod 中增加 CPK/DSC parser、二进制 `pv_db` 解析或新 hook。PV276 的基础包证明已完成后，用户实际目标 PV424 的**官方 DLC**资料成为唯一允许新增的输入；X Song Pack/F2nd、其他 DLC、全曲扫描和通用数据框架仍不是当前架构输入。

## 逆向边界

以下部分属于基础设施，应谨慎修改：

- `mod.cpp` 中的特征签名与地址推导。
- Detours hooks。
- `globals.h` 中逆向结构体的字段偏移。
- DivaModLoader 生命周期导出。

这些实现依赖游戏函数签名、hook 调用约定和游戏内存结构。

## 计划中的 KTV 边界

以下是目标设计，尚未实现：

```text
歌词时间线 → 评估显示状态 → KTV 渲染状态 → 渲染器
```

KTV 层应在不改变逆向边界的前提下，为当前句、下一句、预提示与空白区间生成显示状态。

## 当前批量缓存交付路径（2026-09-27）

```text
资料包清单 → 既有 FarcPack → 已提取 rom/script + 匹配文本表
        → 单曲 DSC 时间线 → JSON/SRT 同源校验报告
        → 所有资料包成功才统一部署为 lyrics/PVxxx.srt
        → 既有 LyricLine / KTV Overlay
```

运行时不会以歌词 hook 回退填充 KTV Overlay；缺少成功缓存即不绘制 Overlay，原版游戏歌词仍由原渲染器显示。最后一句只在 DSC 中有官方 `PV_END` 命令时以该时间闭合；这属于离线资料解释，不新增运行时 hook。

## 资料包完整定位规则（2026-09-27）

完整缓存发现不以一个目录中 `pv_*_normal.dsc` 的数量为结论。权威路径为：文本表 `difficulty.normal.0.script_file_name` → 逻辑 PVID / 物理 DSC 编号映射 → 跨已解包资源根目录定位同名 DSC → 按资料包顺序合并运行时 `PVxxx.srt`。F2nd 可把一个逻辑 PVID 映射到不同 DSC 编号；多个逻辑 PVID 也可共享一个 DSC。部署器的 `replace` 策略记录后者覆盖的源缓存。

## PV 工具 MVP（2026-10-10）

现有歌词运行时保持 SRT → LyricLine → KTV 渲染，歌词功能已由用户验收。新增 scripts/export_lyrics.py 是离线短入口：优先复用已验证来源树，按实际 DML priority/enabled/include 选择来源，整批校验后发布 cache，显式安装通过哈希保护用户 SRT/Ruby。

NonVocalManager 是延迟创建的独立模块，在游戏歌曲声道对增益函数增加可选 Hook，仅控制当前歌曲对象的人声 pair1/3。歌曲路径在原 LoadSongAudio 消费字符串前复制，成功加载后绑定；离开 PV 的恢复与指针清理在原状态切换之前执行。配置在 audio-tools.toml。已确认例外仅在歌曲加载时按实际音频文件名匹配，状态随绑定/离开PV清理；只控制伴奏开关下的条件式提示，不介入声道增益或OBS请求。正式支持名单入口为NON_VOCAL_SUPPORT.md。

ObsManager 复用既有状态/时钟，经有界后台 Named Pipe 发送会话快照到独立 Python Helper；Helper 用 WebSocket 5 控制本机 OBS。游戏帧线程不运行网络，生命周期与 IPC 状态独立加锁。录制所有权只在成功 StartRecord 响应后认领；配置开关在 obs-tools.toml，密码在 Helper 本机私有 JSON。自然结束事件和视频首尾仍待用户游戏验收。

两项开关在新增中文 PV 工具窗口中显示，沿用 Ctrl+G；界面字体将系统雅黑中文范围合并到固定字号默认字体，歌词图集分辨率行为保持原路径。MVP不支持DLL热卸载。


## 振假名成套导出（2026-10-10）

有效资料覆盖完成后的最终 SRT/时间线 → 同ID同全文配对来源 → 固定假名约束与整句来源完整对齐（furigana_alignment.py；Janome只作同音边界参考） → PVNNN.ruby.tsv / ruby.audit.json → 三件套哈希预检安装 → 既有 Ruby 渲染。批量生成仅依赖现成提取树；rebuild-ruby-only 可补齐已成功缓存，不重新解析 DSC 或解包。人工修订文件受安装所有权哈希保护。PV 工具窗口跟随 Lyric 右侧顶部并自适应高度；系统中文 UI 字体除常用范围外显式补齐工具用字。

生成算法、行号映射、运行时读取和校验层次详见 [FURIGANA_ARCHITECTURE.md](FURIGANA_ARCHITECTURE.md)；实测 PV 案例、注音陷阱和待复核问题集中记录在 [FURIGANA_CASEBOOK.md](FURIGANA_CASEBOOK.md)。审计无提示不能作为读音正确的证明；来源不能完整对齐时不发布词典补猜；来源缺失、创意读法或并列歧义保留明确复核状态。

## 歌词段落与提示点布局（2026-10-11）

BuildKtvLineLayouts 从完整时间线推导固定轨道及实际同轨前后关系；空档至少 8000 ms（六秒预告加两秒旧句显示）时从上轨重新开始，不继承全曲行号奇偶。短停顿继续交替。OnImGUI 使用相同布局绘制主歌词、Ruby 和下一句倒计时，提示点跟随待唱句的轨道及起点，并在安全边距内显示。无需新增游戏 Hook 或改变 SRT/Ruby 格式。当前具体视觉规则及长句处理的设计边界以 KTV_SPEC.md 为准。

## 单句运行时宽度适配（2026-10-11）

ktv_geometry.h 将正文实际字形边界、Ruby 词组几何、描边取整、阴影及背景测量集中在共享函数内。GetRuntimeKtvLineGeometry 根据用户字号、当前图集分辨率倍率和镜像安全边距为每行计算临时字号及上/下轨位置；DrawKtvLine 和待唱圆点共用结果，GetRubyPosition 与测量共用 Ruby 几何。超宽句临时缩小，正常句保持配置字号；整句时间和ワイプ时间计算不变。无需新增图集、旁路格式或游戏集成 Hook。
## OBS 自动命名与逐首会话（2026-10-11）

ObsPvSession 只观察既有状态、歌曲加载、PVID 和播放时钟，识别连续播放与重复播放；歌词层不变。ObsManager 从游戏既有等待画面读取当前曲名，从音频管理器只读实际静音状态，以有界 v2 快照送 Helper，后台写每秒状态日志。Helper 录制前暂改 FilenameFormatting，StopRecord 返回 outputPath 后等待输出完全停止，再恢复模板并持续待命；持久恢复记录只保存原 profile/模板。详细流程、边界与验证见 [OBS_CONNECTOR.md](OBS_CONNECTOR.md)。

## 播放列表歌词生命周期（2026-10-11）

LyricManager 在每次 PV POST PROCESS TASK 重建本次 SRT/Ruby，独立于上次是否经 PVsel 结束；loadedPvid 将时间线绑定到本曲。PV_STAGE/PV_WATCH/选曲/菜单清理时间线，PVID 不匹配时渲染入口立即拒绝显示、OnFrame 清除旧数据。相同 PVID 的下一次准备也重建时间线，暂停只改变播放状态。此修复使用现有通知，不新增 Hook；OBS 的逐首会话保持独立。
## 逐行歌手配色与合唱渐变MVP

已有有效PV缓存JSON所记来源 → 生产DSC读取器可选命令观察回调 → 按身份解析角色表及复制槽 → 口型活动阈值/成功失败分支一致性 → PVnnn.singers.tsv及独立审计。运行时继续SRT/Ruby原路径，旁路只添加LyricLine.singers；PVID/完整行数/每行时间及全文有任何不匹配即拒绝整份，缺失或未知回退默认色。不同身份不绑定固定槽位；同身份复制演出角色去重。

SingerPalette含未唱/已唱填充、描边、阴影，按身份保存到独立singer-colors.toml，不覆盖既有freelyrics设置。Lyric面板展示当前歌手及其后的可扩展配置。KtvTextStyle携带每层色彩端点，AddStyledKtvText只修改本次新增顶点颜色；正文及Ruby共享整行横坐标，原ワイプ分区和DX11整体透明合成保持。多人可在横向柔和渐变与全部参与者平均纯色之间切换，不重建字体、不增加shader或Hook。

口型标记是参与推测，不是音频声部真值；剧情无声口型可误判，未实现假名/罗马音对齐、主唱/和声判定或逐字时间。规格、工具及验收边界见 [歌手配色MVP](SINGER_COLORS_MVP.md)。


## 合唱上下窄过渡试用（2026-10-14）

singer_render.h为生产正文/注音与渲染回归共享入口；上下模式按本次文本真实字形高度，通过既有ImGui精细裁剪生成不重叠色带并插值UV，中间20%用四段近似柔和过渡。每层独立配色，等色端点走原路径；横向填唱GPU裁剪、整体透明合成、字体图集与逆向集成都不变。独立配置新增chorus_vertical，缺少时默认试用上下；可以恢复原横向渐变，关闭渐变仍为融合纯色。三方案设计记录见CHORUS_COLOR_DESIGNS.md，方案二未实现，须先避让预热省略号。

## 自动多身份扫描与人工修订层（2026-10-15）

export_lyrics在最终有效来源合并后生成Ruby，再扫描全部缓存的角色表。按身份去重复制槽，多个已知不同身份才调用既有口型算法；不明确资料逐曲记录。manifest版本3统一跟踪SRT/Ruby和歌手三件套及哈希，安装器保护用户修改，按已有安装清单及旧MVP明确哈希迁移所有权并回收过期生成旁路。

manual-singers位于cache快照之外，模板初始auto，人工覆盖独立保存。最终歌手为自动结果加显式人工修订，修订严格绑定全文、时间、编号及总行数；审计保留原自动结果和修订哈希。默认完整导出、Ruby补齐与仅歌手补齐共用此流程，apply_singer_marks.cmd供日常快速应用。运行时仍只读SRT/Ruby/最终singers.tsv，DLL不解析人工模板，也不读游戏资产。

## 性能路径更新（2026-10-16，替代历史原生采集描述）

当前KTV只读整首SRT/Ruby/歌手缓存，不再安装CopyCharsByCount和PVDBLookup，也不采集原生当前句或逐句更新字符集。原版歌词显示Hook仅按showInternalLyrics直接转发。轨道与行几何缓存随时间线、预告、字体版本、输出尺寸及布局装饰失效；Ruby直接UTF-8绘制，合成资源在安全渲染入口预热。OBS仅变化发布，音频UI/保存文件不持音量锁。可选ETW由Init注册，只有WPR启用提供程序时才记录区间和换句；普通运行无计时/写盘。诊断DLL仍为优化Release并提供匹配PDB。细节见PERFORMANCE_INVESTIGATION.md。
## OBS 单曲自然结束状态（2026-10-18）

ObsPvSession::IsEndState统一识别GameResultTask及既有加载/退出状态，结果状态清除prepared/active，保留epoch直到下一次准备。既有ChangeGameState Hook按此分类在原游戏函数前发布结束快照、之后发布准备快照；不新增地址或Hook。ObsManager快照变化通过guard配套条件变量唤醒后台，未变化每秒心跳；网络、封装等待与诊断落盘继续只在后台，游戏线程不等待响应。中途暂停与自然结束按状态区分，不根据停钟或isPlaying单独推断。