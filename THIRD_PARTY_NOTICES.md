# 第三方声明

以下许可证和版权通知随对应分发文件保留。完整许可文本可点击查看；运行与构建方法分别见[安装指南](docs/INSTALL.md)和[构建说明](docs/BUILD.md)。

| 组件 | 分发范围与用途 | 许可证与通知 |
| --- | --- | --- |
| [Dear ImGui](https://github.com/ocornut/imgui) | 固定子模块，设置面板与绘制 | [MIT](LICENSES/Dear-ImGui-MIT.txt) |
| stb（ImGui 内置） | 字体栅格化、矩形打包及文本编辑 | [MIT 选项](LICENSES/stb-MIT.txt)；原源码保留其双许可证 |
| [toml11](https://github.com/ToruNiina/toml11) | 固定子模块，TOML 配置读取 | [MIT](LICENSES/toml11-MIT.txt) |
| [SRT parser](https://github.com/saurabhshri/simple-yet-powerful-srt-subtitle-parser-cpp) | 固定子模块，字幕读取 | [MIT](LICENSES/srtparser-MIT.txt) |
| [Microsoft Detours](https://github.com/microsoft/Detours) | 仓库保留 4.0.1 接口及静态库，用于游戏 Hook | [MIT](LICENSES/Detours-MIT.txt) |
| [Janome](https://github.com/mocobeta/janome) 0.5.0 | 离线注音工具及词典 | [Apache-2.0](LICENSES/Janome-Apache-2.0.txt)及 [IPADIC 通知](LICENSES/Janome-IPADIC-NOTICE.txt)，两者均需保留 |
| [websocket-client](https://github.com/websocket-client/websocket-client) 1.8.0 | OBS Helper 的 WebSocket 传输 | [Apache-2.0](LICENSES/websocket-client-Apache-2.0.txt) |
| [Noto Sans JP](https://github.com/google/fonts/tree/main/ofl/notosansjp) | 安装包附带的开放日文字体 | [SIL OFL 1.1 及版权署名](LICENSES/Noto-Sans-JP-OFL.txt) |

源码依赖提交由 Git 子模块固定；字体下载引用和摘要由 `release-dependencies.json` 固定。源码克隆不包含已忽略的 Python 运行库，可通过 `tools/setup_python_tools.cmd` 准备它们。

当前工程使用 ImGui 内置 stb 后端，没有启用或链接 FreeType；历史项目名称里的 FreeType 不表示安装包包含该运行库。

## 需另行取得的工具

| 工具 | 用途 |
| --- | --- |
| [DivaModLoader](https://github.com/blueskythlikesclouds/DivaModLoader) | 加载游戏 Mod，由使用者安装 |
| [OBS Studio](https://github.com/obsproject/obs-studio) | 可选录制软件，Helper 连接使用者自己的 OBS |
| [MikuMikuLibrary / FarcPack](https://github.com/blueskythlikesclouds/MikuMikuLibrary) | 离线准备游戏资料时使用，未捆绑其二进制 |
| [Open-PD-Script-Editor](https://github.com/nastys/Open-PD-Script-Editor) | 离线工具使用的 opcode 数据库来源，由使用者另行取得 |
| Microsoft Visual C++ 运行库 | Windows x64 运行前提，从 Microsoft 官方取得 |

这些工具和其依赖遵循各自上游许可。本项目不会因引用工具而取得游戏或歌曲素材的分发权，也不代表上游对本项目的背书。
