# 源码构建

需要Git、Visual Studio 2022（C++桌面开发及Windows SDK）。构建入口自动发现VS，优先使用v143，也兼容v142组件。

```powershell
git clone --recurse-submodules https://github.com/HYDlink/DivaKaraoke.git
cd DivaKaraoke
tools\build_release.cmd
```

输出是`artifacts/build/x64/Release/DivaKaraoke.dll`，日志在`artifacts/build/release-build.log`，不会自动部署到游戏。

已有克隆先执行`git submodule update --init --recursive`。GitHub的Source code ZIP不包含子模块源码。

运行离线工具另需Python 3.11+，路径按[歌词工具](LYRICS_EXPORT.md)填写。字体与依赖许可见[第三方声明](../THIRD_PARTY_NOTICES.md)。可以重新构建，但不承诺不同工具链产生逐字节一致的DLL。
