@echo off
chcp 65001 >nul
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe" tools\obs_session_regression.vcxproj /nologo /p:Configuration=Release /p:Platform=x64 /v:minimal >artifacts\obs-playlist-build\会话编译.log 2>&1
if errorlevel 1 exit /b 1
artifacts\obs-playlist-build\obs_session_regression.exe
