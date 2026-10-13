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
