> 历史研发资料，仅供追溯，不是当前操作指南。设备绝对路径已去标识；原始记录保留在私有历史备份及 Git 历史。

# Non-Vocal MVP

正式支持范围及用户实机确认的10首例外见[伴奏模式支持说明](NON_VOCAL_SUPPORT.md)。本页记录技术接线与历史验证依据。

2026-10-10。歌词已按用户口径验收。本功能不解包新 CPK，不替换 OGG，不修改判定、成绩、Combo 或歌词 Hook。

## 交付与接线

独立 NonVocalManager 在 Init 后安装可选 Detours Hook。ImGui 即时开关与保存按钮持久化到 DLL 旁 audio-tools.toml，默认关闭。失败仅停用音频功能。

OnSongAudio 在原歌曲加载函数返回后绑定歌曲对象；只控制同一对象的 pair1/3，pair0/2 伴奏不变。OnGameState 必须在原状态转换之前执行，在 PVsel/MENU/STARTUP 恢复并清理对象。OnFrame 应用开关变化。关闭时恢复最后一次游戏原请求而非固定 100%。默认关闭的歌曲加载不写增益。

## 证据

- 复用 artifacts/pv424-dlc00-extract/rom_steam_dlc/rom/sound/song/pv_424.ogg，ffprobe 确认 4 声道、44100 Hz，未复制或重新提取。
- [DivaDocs Change Vocal](https://docs.divamodarchive.com/User%3ANanase7247/Sandbox)支持标准伴奏/人声布局，但不保证所有 Mod 音频。
- 固定 [ReDIVA c5d784a5](https://github.com/korenkonder/ReDIVA/tree/c5d784a5d417f98b4511889a926943deff9ba35f)的 pv_game_music.cpp 与 ogg_vorbis.cpp 提供 setter 和百分比转 dB 语义参考；没有复制其实现进入 DLL。
- 本机 0x14023F200 是 92 字节 setter：检查 OGG flag4，把第三参数百分比转 float*0.01，调用 0x1405AFCF0 转 dB，取得 this+0xE8 OGG wrapper，调用 0x1405AFB70 设置指定声道对增益。
- 上层 0x14023E920 读取 this+0x1C+pair*4 的主增益，乘原请求百分比后调用 setter，镜像 pair0→2 / pair1→3，最后将原请求保存到 this+0x0C+pair*4。初始恢复值由这些已验证字段计算，后续以实际原请求更新。不是猜测偏移。
- 49 字节签名在本机 EXE 唯一命中，文件偏移 0x23E800；运行时也拒绝第二命中，并核查尾部关键指令，没有固定绝对地址调用。报告：artifacts/non-vocal-research/signature-audit.json；反汇编：pair-volume-disassembly.txt、music-volume-disassembly.txt、ogg-api-disassembly.txt。
- EXE SHA256：6F4DF714C28515C93B3023E7D6DAFA9095DD8835F762D54DB1726FB8BC04504D。函数字节 SHA256：AD3CDBEA643DCBC177C6A374457425E9E60300434E8EE03479AA520E6F8F2002。

## 验收边界

离线签名唯一性与语义为 LOGIC VERIFIED；整体构建由主代理确认 BUILD VERIFIED。真实 Hook、听感、开关恢复和生命周期为 IN-GAME VERIFICATION REQUIRED。本轮未启动游戏。

1. PV424 关闭模式确认原音频与歌词正常，开启后伴奏持续、人声消失。
2. 同曲反复开关，关闭恢复人声；暂停/继续不应意外恢复。
3. 节奏模式确认判定、分数、Combo 未改变，miss 后关闭遵循游戏原增益。
4. 返回选曲、重试、换曲、退出 PV，确认无崩溃与残留静音；保存并重启确认开关保留。
5. 立体声混音无法独立去除已混入伴奏的人声；部分 Mod 曲无分轨，界面已说明。不能报告为通用 AI 去人声。

## 已确认的原始音频例外（2026-10-16）

PV261《君の体温》虽然声明四声道，但整首245.5秒中后两个声道各10826550个采样全部为零，人声和伴奏混在前两个声道。静音pair 1/3无法去除其歌声；四声道标签不能证明实际分轨。源文件哈希、PV424有效声道对照、只读审计脚本及复查命令见[PV261音频证据](research/pv261-non-vocal-audio-evidence.md)。运行时“静音已请求”和录像Off Vocal后缀仍是请求状态，不能证明该曲实际无人声。

## 审计命令示例

下例按要求显式以反斜杠分行；PowerShell 执行时将行尾反斜杠换成反引号。

```bash
python scripts/audit_non_vocal_signature.py \
  --game-exe "${game_dir}/DivaMegaMix.exe" \
  --output "artifacts/non-vocal-research/signature-audit.json"
```
