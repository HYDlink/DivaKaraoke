> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# 已提取资料复用约定

跨项目通用资源入口见[已导出游戏资产与解析资料索引](EXTRACTED_ASSETS_INDEX.md)，含原始资源树、FARC展开报告、目录样例和解析工具；本页保留复用约定。

日期：2026-10-10。用户要求避免重复解包；本轮三路任务均未执行新的资产解包。

## 本机现有入口

权威来源清单为 artifacts/installed-native-lyric-sources.json。官方资料优先就地读取：

- ${extracted_root}/main-extract
- ${extracted_root}/dlc00-extract
- ${extracted_root}/dlc00-region-extract
- ${workspace_root}/artifacts/main-region-extract

Mod 资料直接读取清单中的 extracted_rom，新增输出目录只放派生缓存和报告，不复制资产树。找不到来源时先报告具体缺失项；本轮不得自行全量重解。

## 已核实重复样本

| 内容 | 已存在的位置 | SHA-256 |
| --- | --- | --- |
| PV424 音频 | artifacts/pv424-dlc00-extract 与 ${extracted_root}/dlc00-extract 下同一路径 rom_steam_dlc/rom/sound/song/pv_424.ogg | 01B0D097FF8574AA588E6CE563ABF15FE4163C4EE4074A7250D2BB4E3C2E6236 |
| 基础歌词表 | artifacts/main-region-extract 与游戏根下 diva_main_region 中的 rom_steam_region/rom/pv_db.txt | 23944A7658578D97ACE3484EA63F0822B06555B55EB58AAA513524B8A3271BFC |

此表证明样本文件重复，不代表整个目录完全一致。F: 下还有 main-farc-extract、main-farc-extract-v2 及多个 farc-*-smoke/style-test 历史输出；本轮不删除，后续清理须先核对完整性和清单引用。

## 工具使用依据

既有 CPK 总控实际调用 FarcPack.exe、CPK 路径、输出目录三项；--reuse-extracted 可完全跳过工具。FARC 展开遵循 scripts/expand_farc_tree.py 已验证的 destination + .contents 参数语义，不通过反复试参数产生新目录。不得重新实现 CPK 提取器。
