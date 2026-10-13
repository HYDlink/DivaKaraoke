@echo off
chcp 65001 >nul
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe" tools\ktv_render_regression.vcxproj /nologo /p:Configuration=Release /p:Platform=x64 /v:minimal
if errorlevel 1 exit /b 1
artifacts\lyric-composite-fix-build\ktv_render_regression.exe
