# DivaKaraoke

为《初音未来 Project DIVA Mega Mix+》提供双轨卡拉OK歌词、日文注音、行级歌手配色、伴奏与OBS录制辅助。

**v0.2.0基于2026-10-25第二阶段冻结版。** 使用整句卡拉OK推进，不包含第三版逐字对齐、音频模型或GPU实验。不同曲目的角色活动与伴奏声道存在例外，详见功能说明。

- [安装与升级](docs/INSTALL.md)
- [源码构建](docs/BUILD.md)
- [v0.2.0发布记录](docs/RELEASE_V020.md)
- [歌手配色与人工标记](docs/SINGER_EXPORT_WORKFLOW.md)
- [伴奏支持范围](docs/NON_VOCAL_SUPPORT.md)
- [OBS连接与录制](docs/OBS_CONNECTOR.md)
- [授权与资源范围](LICENSING.md)、[第三方声明](THIRD_PARTY_NOTICES.md)

## 使用

从[Releases](https://github.com/HYDlink/DivaKaraoke/releases)下载，将DivaKaraoke目录放入游戏mods目录，并按安装说明配置DivaModLoader。公开包附带开放许可证日文字体；歌词使用你自己的缓存或从本机游戏导出。旧MMFreeLyrics必须停用，避免两套Hook同时加载。

| 快捷键 | 功能 |
| --- | --- |
| Ctrl+F | 字体设置 |
| Ctrl+G | 歌词、歌手颜色及辅助工具 |
| Ctrl+S / Ctrl+L | 保存 / 读取设置 |

保留原项目的字体、描边、阴影、外挂SRT和样式功能，并增加双轨当前句/下一句、Ruby、分辨率缩放与曲目生命周期处理。伴奏控制与OBS自动录制均为可选功能。

## 来源与署名

本项目是独立维护的GitHub仓库，基于[mos9527/MMFreeLyrics](https://github.com/mos9527/MMFreeLyrics)开发，基线提交`86ca9825bba1e3c6a84a48d05768de4d57288c18`；保留现有上游Git历史。感谢mos9527的原始开发及对源码、二进制修改和再分发的明确授权。此授权不等于上游对本项目维护或背书。

历史开发、研究、验证文档保留于docs。部分文档记录本机E/F盘路径和旧名称；当前安装与构建以本README链接的说明为准。歌曲、游戏、第三方曲包、用户字体及工具各自保留权利，不由本项目统一再授权。
