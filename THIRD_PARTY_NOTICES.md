# 第三方依赖声明

## Dear ImGui

- 仓库：<https://github.com/ocornut/imgui>
- 固定提交：`9aae45eb4a05a5a1f96be1ef37eb503a12ceb889`（标签 `v1.88`）
- 集成路径：`Dependencies/imgui`
- 许可证：MIT License

以下为该依赖 `LICENSE.txt` 保留的许可证通知原文：

```text
The MIT License (MIT)

Copyright (c) 2014-2022 Omar Cornut

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## simple-yet-powerful-srt-subtitle-parser-cpp

- 仓库：<https://github.com/saurabhshri/simple-yet-powerful-srt-subtitle-parser-cpp>
- 固定提交：`38dd4def3eda841d1cb7cf6964a10fd8dbca22f7`
- 集成路径：`Dependencies/srtparser`
- 许可证：MIT License

以下为该依赖 `LICENSE.txt` 保留的许可证通知原文：

```text
MIT License

Original work Copyright (c) 2017 Oleksii Maryshchenko
Modified work Copyright (c) 2017 Saurabh Shrivastava

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## websocket-client

OBS Helper 附带 websocket-client 1.8.0，许可证为 Apache-2.0；完整许可证位于 tools/obs_runtime/websocket_client-1.8.0.dist-info/LICENSE。传输复用该依赖，不自行实现 WebSocket。


## Janome

离线振假名工具附带 Janome 0.5.0，许可证为 Apache-2.0；完整许可证与词典通知位于 tools/furigana_runtime/Janome-0.5.0.dist-info/LICENSE.txt 和 NOTICE.txt。此依赖只在离线导出工具中运行，游戏 DLL 不运行分词器。

## toml11

- 作者：Toru Niina；许可证：MIT。
- 仓库：https://github.com/ToruNiina/toml11
- 固定提交：`1400dd223fb4297337266fcb5d04b700338aea71`。
- 完整通知：`LICENSES/toml11-MIT.txt`；原文件位于`Dependencies/toml11/LICENSE`。

## Microsoft Detours

- Microsoft Corporation；头文件标识版本4.0.1，预编译静态库随历史仓库保留。
- 仓库：https://github.com/microsoft/Detours ，许可证：MIT。
- 上游许可证：https://github.com/microsoft/Detours/blob/v4.0.1/LICENSE.md
- 完整通知：`LICENSES/Detours-MIT.txt`。二进制构建来源尚未完整复核，不能宣称已全源码可复现。

## stb与当前字体后端

ImGui中嵌入的`imstb_truetype.h`、`imstb_rectpack.h`、`imstb_textedit.h`由Sean Barrett及贡献者提供，原文件保留双许可证；本分发保留MIT选项通知，见`LICENSES/stb-MIT.txt`。当前工程未定义`IMGUI_ENABLE_FREETYPE`，也不编译`imgui_freetype.cpp`、不链接FreeType；历史名称及头文件枚举引用不代表安装包包含FreeType运行库。

## Noto Sans JP

公开安装包附带未修改的Noto Sans JP变量TTF，源自Google Fonts官方发布，具体版权署名以随附OFL文件为准，适用SIL Open Font License 1.1，完整版权与许可见`LICENSES/Noto-Sans-JP-OFL.txt`。下载来源为https://github.com/google/fonts/tree/main/ofl/notosansjp ，实际固定提交和SHA-256记录在发布依赖清单中。字体不适用项目代码授权，不能单独售卖字体文件。

## Janome词典与完整通知

Janome 0.5.0适用Apache-2.0，同时包含MeCab IPADIC词典及NAIST/ICOT通知。分发时必须同时保留`LICENSES/Janome-Apache-2.0.txt`与`LICENSES/Janome-IPADIC-NOTICE.txt`，不能只写Janome的许可证名称。websocket-client 1.8.0的完整Apache-2.0许可证另保存在`LICENSES/websocket-client-Apache-2.0.txt`。源码克隆默认不附这两个已忽略的运行库，可用`tools/setup_python_tools.cmd`安装固定版本。

## 外部工具、平台与资源

- DivaModLoader：https://github.com/blueskythlikesclouds/DivaModLoader ，由用户单独安装，未捆绑其DLL。
- MikuMikuLibrary/FarcPack：https://github.com/blueskythlikesclouds/MikuMikuLibrary ，离线提取可选外部工具，公开包不捆绑其二进制或原始游戏资料。请从该项目取得并遵循其许可证及依赖通知。
- Open-PD-Script-Editor：https://github.com/nastys/Open-PD-Script-Editor ，opcode数据库由用户另行取得或通过参数指向已有副本；公开包不重分发数据库或程序。历史验证版本为`93c10c83f9e36e4f45b2cd0404eb99b9a6de1400`。
- OBS Studio：https://github.com/obsproject/obs-studio ，助手只连接用户本机安装的OBS，不捆绑OBS或声称为其官方插件。
- Windows/DirectX/Visual C++运行库属于平台依赖；若需要VC++运行库，请安装Microsoft官方x64 Redistributable，不能复制本机不明来源DLL。
- v0.2.0不包含Yohane、声学模型、PyTorch/CUDA、Demucs或第三版逐字算法。外部歌曲、游戏音视频、商业字体不受上游源码授权覆盖。

历史参考项目链接见Git历史中的原README。上述工具依赖与集成不代表各上游对本项目的背书。
