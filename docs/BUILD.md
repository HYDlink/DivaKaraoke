# 从源码构建

## 准备

- Git。
- Visual Studio 2022 或 Build Tools，安装 C++ 桌面开发与 Windows SDK。构建入口优先使用 v143，也兼容原工程的 v142 组件。
- 运行离线工具时另需 Python 3.11+；构建游戏 DLL 不需要 Python、CUDA 或声学模型。

## 构建 DLL

```powershell
git clone --recurse-submodules https://github.com/HYDlink/DivaKaraoke.git
cd DivaKaraoke
tools\build_release.cmd
```

已有克隆先运行 `git submodule update --init --recursive`。GitHub 自动生成的 Source code ZIP 不包含子模块源码。

输出位于 `artifacts/build/x64/Release/DivaKaraoke.dll`。入口自动发现 VS，不向游戏目录部署，也不需要 7-Zip。详细编译信息位于 `artifacts/build/release-build.log`。

当前使用 ImGui 内置 stb 字体后端，没有启用 FreeType。Detours 预编译库随源码保留，来源与许可证见[第三方声明](../THIRD_PARTY_NOTICES.md)。可以在固定依赖下重新构建，但不承诺不同编译器或构建时间产生逐字节相同的 DLL。

## 路径与工具依赖

按[歌词工具](LYRICS_EXPORT.md)配置自己的 `.local/environment.toml`。运行 `tools/setup_python_tools.cmd` 准备固定版本 Python 依赖。设备路径和私密认证不写进公共文档。

## 打包与检查

以下多行命令使用 Git Bash；PowerShell/CMD 可合并为一行。输出目录必须是新的，不覆盖已有发布。

```bash
python scripts/prepare_release_assets.py
python scripts/package_public_release.py \
  --output-dir artifacts/public-release
python scripts/verify_public_package.py \
  --zip artifacts/public-release/DivaKaraoke-v0.2.1-win64.zip \
  --output-dir artifacts/clean-install-check
```

以 `config.toml` 版本号和实际生成的文件名为准。公开安装包只收录经过选择的用户文档、日常工具和合法分发依赖，不收录本地配置、历史归档或开发验收流水。

发布版本的源码、二进制、校验清单与验证结果必须相互对应。已发布标签与附件不随文档改动覆盖；需要修正安装包时发布新的维护版本。
