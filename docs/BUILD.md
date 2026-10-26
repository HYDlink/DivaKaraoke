# 从源码构建

需要Git、Visual Studio 2022或Build Tools 2022，安装“使用C++的桌面开发”、MSVC v143（或原项目的v142兼容组件）与Windows 10/11 SDK。无需安装FreeType：当前工程使用ImGui内置stb后端，保留了上游的FreeType枚举引用。

```powershell
git clone --recurse-submodules https://github.com/HYDlink/DivaKaraoke.git
cd DivaKaraoke
tools\build_release.cmd
```

已有克隆先执行`git submodule update --init --recursive`。三个公开子模块的固定提交见`THIRD_PARTY_NOTICES.md`，不再依赖上游旧私有srtparser。构建入口用vswhere自动发现Community、Professional、Enterprise或Build Tools，不要求特定VS安装路径；优先v143，旧安装回退到v142及v160构建目标。输出为`artifacts/build/x64/Release/DivaKaraoke.dll`，不会自动写游戏目录，不需要7-Zip。

Detours随仓库保存4.0.1头文件与预编译x64静态库，保留MIT通知。当前只能保证固定依赖下可以重新构建，尚未宣称跨工具链DLL逐字节一致；其原预编译库的完整构建来源尚待复核。需要全部源码重建时从Microsoft/Detours v4.0.1自行构建x64库后替换本地构建输入，并记录编译器版本。

运行`tools/setup_python_tools.cmd`准备Python外围工具依赖。游戏DLL不需要Python、CUDA或任何声学模型，v0.2.0没有第三版口型逐字、音频逐字及相关GPU依赖。

发布打包入口与验证记录见`RELEASE_V020.md`。历史测试脚本里仍保留原开发路径，不能当作新电脑的一键验收入口；它们作为有价值的研究工具保留。正式构建和发行安装入口均使用上述可迁移路径。
