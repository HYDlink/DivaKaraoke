# PV276 原版原生歌词证据

日期：2026-09-27。本文记录原版原生歌词 M0 的可复查结果；不是运行时提取器，也不包含完整歌词副本。

## 输入与来源

两份输入均来自本机已提取的原版 MM+ 目录：

| 输入 | 路径 | SHA-256 |
| --- | --- | --- |
| 原版歌词表 | `E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\diva_main_region\rom_steam_region\rom\pv_db.txt` | `23944A7658578D97ACE3484EA63F0822B06555B55EB58AAA513524B8A3271BFC` |
| 原版 Normal DSC | `E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\diva_main_region\rom_steam_region\rom\script\pv_276_normal.dsc` | `50795E2425EE4AC7A732B4882B469C1A64E374FB105FC9DDFCF6647BAD4E87A7` |

`pv_db.txt` 中存在连续完整的 `pv_276.lyric.001` 至 `pv_276.lyric.050`，共 50 行。原版提取目录也包含该 PVID 的 Easy、Normal、Hard、Extreme DSC；本验证固定使用 Normal，避免混合难度样本。

## 读取依据

本次没有在项目中新增 DSC parser。只读诊断严格采用 [Open-PD-Script-Editor 的 Future Tone `readAll`](https://github.com/nastys/Open-PD-Script-Editor/blob/touchbar/DSC.cpp)：跳过 4 字节头部，按其 `opcode_db/db.json` 的 `info_FT` 参数长度逐条读取 32 位小端命令。

该数据库定义 `TIME` 为 opcode 1、1 参数，`LYRIC` 为 opcode 24、2 参数。该工具的 [pdtime.cpp](https://github.com/nastys/Open-PD-Script-Editor/blob/touchbar/pdtime.cpp) 按每秒 100000 个单位拆分时间；[Project-DS 格式说明](https://github.com/Hydr8gon/Project-DS/blob/master/notes.txt) 也独立说明 `TIME` 参数单位为 10^-5 秒、`LYRIC` 的参数 1 是歌词索引、0 表示清屏，参数 2 通常为 -1。

## 结果

- 该 Normal DSC 共读取 1018 条命令，没有遇到 Future Tone opcode 数据库未定义的 opcode。
- 读取到 64 个 `LYRIC` 事件：50 个非零 ID 与 `pv_276.lyric.001–050` 一一命中，14 个 ID 0 清屏事件。
- 所有观察到的第二参数均为 `-1`。
- 下表只保留首段少量原始证据；完整文本仍以用户本机原版 `pv_db.txt` 为准。

| DSC 原始时间值 | 换算时间 | LYRIC ID | 原版文本/状态 |
| ---: | ---: | ---: | --- |
| 749833 | 00:00:07.49833 | 1 | 「よっ！初音屋！」 |
| 873999 | 00:00:08.73999 | 0 | 清屏 |
| 1478999 | 00:00:14.78999 | 2 | 一、二、一二三 Yo! |
| 1833166 | 00:00:18.33166 | 3 | へい旦那　Break it down now |
| 1999833 | 00:00:19.99833 | 4 | バブルなり全員集合 |

## 结论与边界

**LOGIC VERIFIED（原版数据关联）**：原版 DSC 已提供完整、有序的未来歌词 ID/时间事件，原版 `pv_db.txt` 已提供这些 ID 的日文文本。因此离线生成完整 `LyricLine` 时间线在技术上可行，运行时将能在当前行开始前查询未来下一行。

**IN-GAME VERIFICATION REQUIRED（同步）**：尚未在 PV276 的首句、中段、尾句把换算时间与 `currentPlaybackTime` 截图对照；在完成三点同步前，不能宣称最终 KTV 时间偏移已验证。

下一项最小实现任务应是只处理已提取原版 `pv_276_normal.dsc + pv_db.txt` 的离线提取器，输出可审核的 `PV276.json`；不开始全曲、DLC、X Song Pack、运行时新 hook 或视觉功能扩展。
