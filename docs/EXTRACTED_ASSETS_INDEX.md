# 已导出游戏资产与解析资料索引

更新时间：2026-10-15。用途：供其他Mod项目预研时只读复用现有资源，与歌词渲染功能无关。本文件记录已看到的资产目录、展开报告和解析入口，不代表所有资源格式都完成了结构或语义解析。

## 新项目先读哪里

1. 本索引：定位游戏原始资料、FARC内文件和工具。
2. [已提取资料复用约定](EXTRACTED_ASSET_REUSE.md)：既有目录复用、工具调用和避免重复提取的约定。
3. 按目标读取对应资源及其报告，再选择小样验证解析方法。新项目的目标、计划与写入范围由新项目决定；本索引不要求继承歌词工程的历史任务。

## 已解包的CPK资料

| 路径 | 内容与用途 |
| --- | --- |
| F:/DivaKaraOkeLyrics/main-extract | 基础包资源树；含rom、rom_ps4、rom_ps4_patch、rom_steam及多个地区/平台目录，优先从这里定位原始资源。 |
| F:/DivaKaraOkeLyrics/dlc00-extract | 官方DLC00资源；本机已见rom_steam_dlc/rom，含脚本、演出、对象、动作、音频等目录。 |
| F:/DivaKaraOkeLyrics/dlc00-region-extract | DLC地区资料；主要入口rom_steam_region_dlc/rom/mdata_pv_db.txt。 |
| D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/artifacts/main-region-extract | 已定向提取的地区数据库；rom_steam_region/rom下已见pv_db.txt、gm_module_tbl.farc、gm_customize_item_tbl.farc；这是定向资料入口。 |
| E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods | 已安装Mod的原始rom目录与数据库；各包是否实际生效还要看当前DML enabled、priority与include。 |

基础包rom下已经看到下列目录/样例，可用于按研究方向定位；这里列文件名，不宣称这些格式都已转换成通用编辑格式：

| 目录 | 已见样例 | 可作为哪些预研的入口 |
| --- | --- | --- |
| script | pv_001_easy.dsc等 | PV脚本指令与时间安排。 |
| auth_3d | CAMPV001.farc、auth_3d_setting.bin | PV演出资源与对应a3da数据。 |
| rob | mot_CMN.farc、mot_HAK.farc | 动作包及内部二进制。 |
| objset | stgd2ns069.farc | 对象/场景资源包。 |
| 2d | aet_adv_cmn.bin、aet_cmn_all.bin等 | 2D/AET/SPR资源。 |
| sound | button.farc、pv600_effect.farc及各子目录 | 音频/音效相关资料；DLC歌曲音频路径已有样例证据。 |
| pv_expression | exp_PV238.bin、exp_PV239.bin | PV表情相关二进制。 |
| light_param、stage_param、skin_param、ibl | face_d2ns048.txt、coli_no_ring.txt、*.ibl等 | 光照、场景、参数与环境资源。 |

相同文件名可能出现在不同平台、补丁、地区或Mod目录；应结合目标资源的引用关系与有效加载来源选择版本，不能只凭第一个同名文件确定。

## 已展开的FARC资料：优先查现成结果

| 展开目录 | 对应报告 | 报告记录 |
| --- | --- | --- |
| F:/DivaKaraOkeLyrics/main-farc-extract-v2 | F:/DivaKaraOkeLyrics/main-farc-extract-v2-report.json | 基础包输入main-extract：成功7659、跳过0、失败0。 |
| F:/DivaKaraOkeLyrics/f2nd-song-farc-extract | F:/DivaKaraOkeLyrics/f2nd-song-farc-extract-report.json | 输入已安装F2nd Song Pack：成功528、跳过0、失败0。 |
| F:/DivaKaraOkeLyrics/misaki-max-farc-extract | F:/DivaKaraOkeLyrics/misaki-max-farc-extract-report.json | 输入已安装Misaki & Max's 3DPV Pack：成功77、跳过0、失败0。 |

上表是读取现有报告所得，2026-10-15检查了目录与部分实际文件，未逐个重新哈希整树。成功数量指报告中处理的FARC项，不是PV数量，也不是全部游戏资产数量。DLC00的CPK级资料已存在；本次索引没有确认其独立全量FARC展开报告。

展开路径保留输入相对目录，使用FARC文件名作为输出目录名。例如：

- F:/DivaKaraOkeLyrics/main-extract/rom/auth_3d/CAMPV001.farc
- 对应目录F:/DivaKaraOkeLyrics/main-farc-extract-v2/rom/auth_3d/CAMPV001.farc/
- 其中已看到CAMPV001_BASE.a3da、CAMPV001_PARTS02.a3da等。
- rob/mot_CMN.farc/内已看到mot_CMN.bin；2d/spr_cmn_all.farc/内已看到spr_cmn_all.bin。

报告每项含source、output、status及部分files计数，可直接按目标包定位现成结果。F:/DivaKaraOkeLyrics/main-farc-extract及farc-*-smoke/style-test等历史目录也存在；优先按匹配报告和文件内容选来源，保持原处，不自行去重删除。

## 现有工具与解析入口

所有相对路径均相对D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/。

| 路径 | 当前可以复用的内容 | 已验证范围 |
| --- | --- | --- |
| MikuMikuLibrary/FarcPack.exe | 已有CPK提取和FARC展开工具。 | 本工程已有实际调用与展开报告。 |
| scripts/expand_farc_tree.py | FARC展开总控，支持按相对路径glob定向、复用已有结果及失败报告。 | 既有流程；先查现成展开目录，仅缺目标时再考虑定向提取。 |
| MikuMikuLibrary/DatabaseConverter.exe | 已存在的数据库转换工具。 | 文件存在；目标格式、参数和转换正确性需在新项目按小样验证。 |
| MikuMikuLibrary/MikuMikuModel.exe及MikuMikuLibrary.dll | 已存在的资源工具及库。 | 文件存在；没有在本工程验证所有模型、材质、动画等导出能力。 |
| artifacts/Open-PD-Script-Editor/opcode_db/db.json | 已有DSC opcode表，包含FT信息。 | 已用于现有Future Tone格式读取器。 |
| scripts/extract_native_lyric_timeline.py::read_lyric_events | 生产DSC读取器，带可选command_observer回调。 | 原返回值围绕歌词，但回调能取得现有读取器解码的全部命令，不需要重写二进制parser。 |
| scripts/build_singer_timeline.py::read_commands | 可直接复用的完整命令收集入口。 | 返回命令名、参数、文件偏移、raw_time及分支/角色上下文；函数名所在文件与歌手有关，但命令收集本身不局限于口型。 |

现有代码能够解码DSC指令，不代表相机、动作、AET、对象等每种指令参数都已完成语义验证。FARC展开得到.a3da或.bin，也不等于已经转成JSON、FBX、PNG、WAV等格式。新项目应分别记录容器提取、结构解析、语义验证三层进度。

## 已有解析产物的可用部分

- artifacts/singer-full-export/cache/PVnnn.singers.audit.json：62首候选的现成完整DSC命令记录，可按commands查看非歌词命令；审计还含来源路径/哈希。选择哪些PV有此审计由当时多身份扫描决定，不能据此推断其他PV没有脚本。
- artifacts/singer-full-export/cache/PVnnn.json：309首有效时间线缓存，source.dsc、source.pv_db、source.opcode_db可用于追溯实际来源；正文围绕歌词，不是通用游戏资源数据库。
- artifacts/installed-native-lyric-sources.json：已有资料包和PV文本/脚本映射来源，能协助定位基础包/DLC/Mod；它是歌词流水线的来源清单，不是模型、纹理、音频等资产的完整总目录。
- artifacts/singer-full-export/build-sd751skr/effective-sources.json：该次导出按当前DML筛选后的来源与文本指纹；这是一次运行的快照，Mod配置改变后需重新核对。

解析其他Mod需求时，优先沿source或FARC报告回到实际原始资源；逻辑PVID可能映射到不同的物理DSC编号。

## 给新项目的起始说明

可直接把下面这段放到新项目的预研请求：

> 先只读D:/Work/Projects/VibeCoding/DivaKaraOkeLyrics/docs/EXTRACTED_ASSETS_INDEX.md和docs/EXTRACTED_ASSET_REUSE.md，复用F:/DivaKaraOkeLyrics/现有CPK解包树、FARC展开树及对应报告。根据本项目具体Mod目标定位资源，先查已导出结果，避免重复全量解包；新增研究结果写入新项目目录。DSC优先复用现有读取器和opcode表，其他格式先验证现成工具。明确区分已解包、已结构解析与已验证语义，不把歌词工程的历史任务范围套到本项目。

本轮仅整理索引，没有启动新项目、重新解包、搬迁资产或修改游戏文件。
