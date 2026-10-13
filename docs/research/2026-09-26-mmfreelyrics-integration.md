# MMFreeLyrics 集成调查记录

> 本文是针对上游源码的历史证据记录，不是当前架构的实时说明。后续架构变化不得回写或改写本调查结论。

## 调查对象

- 仓库：`mos9527/MMFreeLyrics`
- 已调查提交：`86ca9825bba1e3c6a84a48d05768de4d57288c18`
- 提交说明：`mod : fix address for 1.03 / 1.04`

## 仓库概览

项目是 x64 Windows DLL Mod。`Source/MMFreeLyrics.vcxproj` 指定 `DynamicLibrary`，使用 Detours、ImGui、DX11、FreeType、toml11 与 SRT parser。核心文件为 `Source/mod.cpp`、`Source/globals.h`、`Source/managers/lyric_manager.*`、`Source/managers/font_manager.*` 和 `Source/utils/config.*`。

## 运行时架构

```text
DivaModLoader
  → MMFreeLyrics DLL
    → 特征签名扫描与 Detours hooks
      → PV/PVID/播放状态
        → LyricManager
          → SRT 时间线/当前歌词
            → ImGui
              → DX11
```

`Source/mod.cpp` 导出 `D3DInit`、`Init`、`OnFrame`；它安装 hooks，创建 ImGui Context，并在每帧将 ImGui draw data 交给 DX11。

## PVID 来源

`Source/mod.cpp` 使用 `sigpv_selector_switch__PvSelector__applySel` 签名，再通过 `readRelCall16Address(... + 0x1D0)` 取得 `getPvSelAddr`。`Source/globals.h` 的逆向 `PvSelector` 结构包含 `PVID` 字段。`LyricManager::OnLyricsBegin()` 读取 `pvsel->PVID` 并加载 `lyrics/PV%03d.srt`。

PVID 不是公开 DivaModLoader API；它依赖签名扫描、地址推导与逆向结构字段。

PV 开始由游戏状态字符串 `PV POST PROCESS TASK` 触发，结束由 `PVsel` 触发，二者均在 `_ChangeGameState` hook 中交给 `LyricManager::UpdateGameState()`。

## 播放时间来源

`_DivaPlayback` hook 在 `Source/mod.cpp` 保存 `DivaPlaybackStatus*`。`Source/globals.h` 的该结构含 `currentPlaybackTime`。`LyricManager::TimeElapsed()` 直接返回此浮点字段，并在查询 SRT 时乘以 1000 转为毫秒。

代码按秒使用该时间，且不是帧累计时间。源码还从 `DivaPlaybackStatus2::isPlaying` 读取播放/暂停状态。实际游戏中对暂停、跳转和鉴赏模式边界的行为尚未验证。

## 歌词数据流

```text
PVID → lyrics/PV###.srt → SubtitleParserFactory → SubtitleParser
     → vector<SubtitleItem*> externalLyrics
     → SubtitleItem::getByTimestamp(毫秒)
     → getText() → ImGui Overlay
```

`LyricManager::GetCurrentLyricLine()` 使用 `SubtitleItem::getByTimestamp(externalLyrics, TimeElapsed() * 1000 + exSubOffset)` 选择当前项，再调用 `getText()`。

游戏内原始歌词是不同路径：`_UpdateLyrics` 记录索引，`_CopyCharsByCount` 在长度 `0x4C` 时捕获文本，随后存入私有 `internalLyricLine`。该路径没有下一句时间线。

没有显式 next lyric 抽象。`externalLyrics` 是 `LyricManager` 私有成员，没有全局可访问的公开时间线。

## 渲染管线

`FontManager::RebuildFonts()` 使用 `ImGui::Fonts->AddFontFromFileTTF()` 建立 FreeType 字体图集，并设置填充、描边、阴影与字体大小。`LyricManager::OnImGUI()` 创建 `Lyric Overlay` 窗口并使用 `ImGui::Text(text)` 绘制单行文本。`OnFrame()` 最终调用 `ImGui_ImplDX11_RenderDrawData()`。

现有选择与单行渲染均在 `LyricManager::OnImGUI()`，因此增加第二行主要影响 `lyric_manager.*`。如果当前/下一句需要独立字号、描边或阴影，才需要扩展 `font_manager.*` 与配置。

## 公开 API 调查

结论：**PARTIAL**。

已发现、且使用 `extern "C"` 与 `__declspec(dllexport)` 导出的仅有：`D3DInit`、`Init`、`OnFrame`。它们服务于 Mod Loader 生命周期。

未发现 `GetCurrentLyric()`、`GetLyrics()`、`GetPVTime()`、`GetPVID()`、`RenderLyrics()` 等 API，也未发现 `.def`、共享 API struct、IPC、回调注册或面向其他 Mod 的公开头文件。`LyricManager_Inst`、`FontManager_Inst`、`pvsel` 与 `playbackStatus` 都是未导出的 C++ 全局状态。

因此不修改 MMFreeLyrics 时，另一个 DLL 无法安全共享其歌词时间线、字体对象或游戏状态；仅复用 SRT 文件命名规则是可行的。

## 方案比较

### A — 修改 / Fork MMFreeLyrics

可直接复用 PVID、播放时钟、PV 生命周期、SRT 加载、字符集构建、字体、ImGui、DX11 与配置。KTV 行级 MVP 的主要改动预计集中在 `lyric_manager.*`。风险为 **Medium**：KTV 逻辑较局部，但既有游戏 hook 和逆向结构对游戏版本敏感。

### B — Companion Mod

没有正式运行时 API，必须重复 PVID/时钟/PV 生命周期 hooks、SRT、字体、DX11/ImGui 与配置；还可能与现有 ImGui Context、WndProc 与相同 hook 冲突。结论：技术可行，但不现实地复用 MMFreeLyrics。

### C — 完全独立 Mod

布局和 SRT 解析相对简单，但 PVID、播放时钟和游戏生命周期是逆向/hook 高风险工作。总体风险为 **High**。

### D — 小型共享核心

当前 parser、时间线、全局游戏状态与 ImGui renderer 紧耦合，尚不适合为单一 KTV MVP 先抽通用核心。只有第二个真实 Mod 需要同一能力时再评估。

## 许可发现

**NO LICENSE FILE FOUND**。

已在上游仓库根目录与受版本控制文件中检查 `LICENSE*`、`COPYING*`，未发现许可证文件；README 没有许可证段落，源码没有许可证头。未推断任何授权范围。

## 最小相关代码面

- `Source/mod.cpp`：理解加载器导出、初始化和现有 hooks；KTV MVP 通常无需修改。
- `Source/globals.h`：理解 PVID 和播放时间的逆向来源。
- `Source/managers/lyric_manager.h`：歌词时间线与状态定义。
- `Source/managers/lyric_manager.cpp`：SRT 查询、当前/下一句选择、空白区间与双行渲染的主修改面。
- `Source/managers/font_manager.*`：仅在需要两套独立字体样式时深入。
- `Source/utils/config.*`：仅在需要持久化 KTV 参数时修改。

无需阅读大量代码；KTV MVP 的重点是 `mod.cpp`、`globals.h` 与 `lyric_manager.*`。

## UNKNOWN / NOT VERIFIED

- `SubtitleItem` 的实际开始/结束时间访问 API与相邻项目遍历 API：**UNKNOWN**。仓库声明的 `mos9527/srtparser` 子模块远程地址要求认证，依赖源码未能检出。
- 真实游戏中 `currentPlaybackTime` 对暂停、跳转与 PV 鉴赏模式边界的表现：**NOT VERIFIED**。
- 原始上游项目在当前环境是否可构建、可加载：**NOT VERIFIED**。

## 后续基线调查附记（2026-09-26）

这是对构建可用性的后续事实记录，不改变上述上游源码调查结论。

- `Source/MMFreeLyrics.vcxproj` 的 Release/x64 配置要求 `PlatformToolset=v142`。
- 当前机器安装有 Visual Studio Enterprise 2022 17.8.3 与 MSBuild 17.8.3，但未安装 v142；基线构建失败为 `MSB8020`，尚未进入编译阶段。
- 公开 README 指向 `saurabhshri/simple-yet-powerful-srt-subtitle-parser-cpp`。该公开项目文档声明 `SubtitleItem::getStartTime()`、`getEndTime()` 和 `getText()`；但尚未证明它与 `mos9527/srtparser` 的固定子模块提交完全一致，因此不能将其作为本项目 API 的已验证事实。
