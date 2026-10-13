# DIVA 原生歌词时间线研究

> **当前范围优先级（2026-09-27）**：基础包 PV276 已完成首个原版证据；现在只允许将用户目标 PV424 的**官方 DLC** `mdata_pv_db.txt` 与同 PVID DSC 纳入验证。此前来自 X Song Pack/F2nd 或明文 `mod_pv_db` 的本地观察仅属探索，不得作为主验证证据。当前权威交接见 `docs/CURRENT_HANDOFF.md`。

## 目标

验证能否从 Mega Mix+ 原生 PV 数据重建完整的：

```text
PVID → { startMs, endMs, text }[] → KTV 当前句 / 下一句 / 预告 / 空白区
```

本研究只关注得到整首 PV 的 `{时间, 歌词文本}`，不扩展为通用 DIVA 资产框架。

## 已知事实

- MMFreeLyrics 已能提供当前 PVID、PV 生命周期、`currentPlaybackTime`、DX11/ImGui 渲染和当前歌词显示 hook。
- 现有 `_CopyCharsByCount` hook 只在游戏已经执行当前歌词渲染时得到文本；这是一个反应式显示路径，不代表未来歌词数据不存在。
- 项目已有独立 `LyricLine` 表示，渲染器无需知道其来源是原生数据、缓存还是 SRT。
- DivaScript（DSC）是 DIVA PV/谱面命令的二进制脚本格式；社区资料表明其可能包含时间与歌词命令。该点尚未在本机 Mega Mix+ 原始文件上验证。

## 待验证假设

| 假设 | 当前状态 | 所需证据 |
| --- | --- | --- |
| Mega Mix+ DSC 有完整的 `TIME` 事件 | **HYPOTHESIS** | 一份真实提取 DSC 的命令序列。 |
| DSC 有歌词事件及可解析的歌词 ID | **HYPOTHESIS** | 事件格式、参数位置和至少三条真实事件。 |
| 歌词 ID 可在原版 `pv_db.txt` 解析成日文文本 | **HYPOTHESIS** | 同一原版 PVID 的 ID→日文文本映射。 |
| DSC 时间可稳定换算为 `currentPlaybackTime` 的毫秒 | **HYPOTHESIS** | 首句、中段、尾句三点对照。 |
| 不同难度 DSC 的歌词事件语义一致 | **UNKNOWN** | 同一 PVID 至少两个难度文件对照。 |
| DLC 与社区 Song Mod 可复用同一流程 | **UNKNOWN** | 各一份实际资产样本。 |

## 两条技术路线

### A. 游戏运行时解析原生数据

在 PV 开始时寻找游戏内已解析的 DSC/pv_db 缓冲区并读出未来事件。

- 优点：无需预生成缓存。
- 风险：可能需要新的版本敏感结构体偏移、指针或 hook；当前没有已验证的安全入口。
- 当前结论：**NOT EVALUATED**，不可据此添加逆向 hook。

### B. 离线原生时间线提取器（优先研究）

在已提取的 DSC 与 pv_db 输入上离线生成最小 JSON 缓存：

```json
{
  "schema_version": 1,
  "pv_id": 424,
  "lines": [
    { "start_ms": 12500, "end_ms": 16700, "text": "..." }
  ]
}
```

- 优点：确定性、可 diff、可测试、不增加游戏 hook、运行时只加载 `LyricTimeline`。
- 风险：需要找到/提取真实资产并验证格式、时间和文本映射。
- 当前结论：**CANDIDATE — PREFERRED FOR MVP**，尚未实现。

## 资料与工具调查原则

优先复用已验证的 DIVA 生态工具/库解析 DSC、pv_db 或已提取资产；不因“可能有 CPK”而新写 CPK 提取器。首个工具接口可以只接受已提取文件：

```text
NativeLyricExtractor --pv-id 424 --dsc <file> --pv-db <file> --out PV424.json
```

这只是候选接口，不代表工具已创建。

## M0 验证顺序

1. 使用已有 MikuMikuLibrary/FARC Pack CPK 提取能力，从原版 `diva_main_region.cpk` 取得 `rom_steam_region/rom/pv_db.txt`（已完成导出）。
2. 在其中定位一首已知原版 PVID 的完整 `pv_xxx.lyric.NNN` 文本表。
3. 定位同一 PVID 的原版 DSC，并参考 Open-PD-Script-Editor 的既有 `DSC.cpp/.h` 列出 `TIME` 与歌词事件；不从零写 parser。
4. 证明歌词 ID→日文文本映射。
5. 证明时间单位、绝对/相对语义和同一时间多个事件的处理。
6. 拼出数行 `{time, text}` 原始证据。只有通过后，才创建离线提取器 MVP、JSON golden fixture 和运行时缓存加载。

## 终止条件

- **SUCCESS**：一首真实 PV 已从 DSC + pv_db 生成并验证完整行级时间线。
- **ARCHITECTURAL BLOCKER**：实际 DSC/pv_db 经检查不能提供未来行文本与时间，附精确证据。
- **TOOLING BLOCKER**：缺少可读资产或可信提取工具，说明所需文件/操作。

## 非目标

- 不做在线歌词服务、自动下载或网络 API。
- 不做全量歌曲扫描、CPK 框架、音频解码、PV/镜头/动作解析。
- 不做字级或音节级时间，除非真实原生数据另有明确证据。
