@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0.."
set "DIVA_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%DIVA_VSWHERE%" goto missing
for /f "usebackq delims=" %%I in (`"%DIVA_VSWHERE%" -latest -products * -property installationPath`) do set "DIVA_MSBUILD=%%I\MSBuild\Current\Bin\MSBuild.exe"
if not defined DIVA_MSBUILD goto missing
for %%I in ("%DIVA_MSBUILD%\..\..\..\Microsoft\VC") do set "DIVA_VCROOT=%%~fI"
set "DIVA_VCTARGETS=%DIVA_VCROOT%\v170"
set "DIVA_TOOLSET=v143"
if not exist "%DIVA_VCTARGETS%\Platforms\x64\PlatformToolsets\v143\Toolset.props" (
  set "DIVA_VCTARGETS=%DIVA_VCROOT%\v160"
  set "DIVA_TOOLSET=v142"
)
if not exist "artifacts\build" mkdir "artifacts\build"
set "DIVA_PROJECT=Source\DivaKaraoke.vcxproj"
if not "%~1"=="" set "DIVA_PROJECT=%~1"
echo 正在构建DivaKaraoke，详细编译信息保存到artifacts\build\release-build.log。
"%DIVA_MSBUILD%" "%DIVA_PROJECT%" /nologo /m /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=%DIVA_TOOLSET% /p:VCTargetsPath="%DIVA_VCTARGETS%\\" /p:PostBuildEventUseInBuild=false /v:minimal >artifacts\build\release-build.log 2>&1
set "DIVA_RESULT=%errorlevel%"
if not "%DIVA_RESULT%"=="0" goto failed
echo 构建成功，输出位于对应工程的artifacts目录。
popd
exit /b 0
:missing
echo 缺少Visual Studio 2022 C++构建工具，请安装桌面C++工作负载和Windows SDK。
popd
exit /b 2
:failed
echo 构建失败，请查看artifacts\build\release-build.log。
popd
exit /b %DIVA_RESULT%
