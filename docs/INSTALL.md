# 安装与升级

## 安装前需要什么

- Windows x64 版《Project DIVA Mega Mix+》。
- 已安装并启用 [DivaModLoader](https://github.com/blueskythlikesclouds/DivaModLoader)。
- [Microsoft Visual C++ 2015–2022 x64 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

游戏中的歌词显示不需要 Python。离线歌词工具和 OBS 助手需要 Python 3.11 或更新版本。

## 安装

1. 从 [Releases](https://github.com/HYDlink/DivaKaraoke/releases) 下载 `DivaKaraoke-版本号-win64.zip`，不要把 GitHub 自动生成的 Source code ZIP 当安装包。
2. 将压缩包中的整个 `DivaKaraoke` 文件夹解压到你自己的游戏 `mods` 目录。
3. 如果游戏根目录的 DML `config.toml` 配有 `priority` 白名单，将 `DivaKaraoke` 加入列表。没有这个字段则不必为本 Mod 新建它。
4. 启动游戏，按 **Ctrl+F** 或 **Ctrl+G**，确认能打开设置面板。

安装后的关键文件如下，目录从你自己的游戏位置开始：

```text
mods/
└─ DivaKaraoke/
   ├─ DivaKaraoke.dll
   ├─ config.toml
   ├─ fonts/
   ├─ lyrics/
   ├─ tools/
   └─ scripts/
```

## 准备歌词

发行包提供开放许可证日文字体，不预置游戏派生歌词缓存。

- 已有自己的缓存：把 `PV编号.srt`、同曲的 `.ruby.tsv` 和可选 `.singers.tsv` 放入 `lyrics`。
- 还没有缓存：按[歌词工具](LYRICS_EXPORT.md)从自己拥有的游戏/曲包资料生成。
- 只有 SRT：可以显示行级歌词；注音和歌手配色需要对应旁路文件。
- 没有完整时间线：使用原生当前句回退，不能预显示还未取得的下一句。

先播放一首你已准备缓存的歌曲，确认当前句、下一句和读音显示正确，再调整样式。

## 升级与迁移

先退出游戏，备份旧 Mod 的配置、`lyrics` 和自有 `fonts`。从旧版迁移时保留需要的 `freelyrics.toml`、`singer-colors.toml`、`audio-tools.toml`、`obs-tools.toml`，不要用默认文件覆盖自己改过的设置。更换目录后如字体未生效，在 Ctrl+F 中重新选择字体并保存。

### 与 MMFreeLyrics 共存

两个目录可以同时保留，不需要删除原版。DivaKaraoke 不依赖旧 `MMFreeLyrics.dll`。

两者会接管部分相同的游戏入口，同时启用尚未完成兼容验证，可能重复显示歌词或响应快捷键。**建议每套游戏配置只启用一个。** 可在旧 Mod 的 `config.toml` 中设 `enabled=false`，或通过你使用的 DML 加载配置切换。只隐藏面板不等于停用 Mod。

## 常用操作

| 按键 | 功能 |
| --- | --- |
| Ctrl+F | 字体、字号、描边和阴影 |
| Ctrl+G | 歌词布局、歌手配色、伴奏和录制工具 |
| Ctrl+S | 保存设置 |
| Ctrl+L | 重新读取设置 |

下一步：[OBS 录制](OBS_CONNECTOR.md) · [伴奏模式](NON_VOCAL_SUPPORT.md) · [歌手配色](SINGER_EXPORT_WORKFLOW.md) · [常见问题](TROUBLESHOOTING.md)
