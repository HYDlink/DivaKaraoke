@echo off
chcp 65001 >nul
setlocal
set "SINGER_TOOL=%~dp0build_singer_timeline.py"
if exist "%~dp0..\scripts\build_singer_timeline.py" set "SINGER_TOOL=%~dp0..\scripts\build_singer_timeline.py"
if not exist "%SINGER_TOOL%" (
  echo 未找到歌手标记工具，请核对工具目录。
  exit /b 2
)
if not "%~1"=="" goto arguments
set "SINGER_CACHE=%~dp0..\artifacts\exported-lyrics\cache"
if not exist "%SINGER_CACHE%\export-manifest.json" set "SINGER_CACHE=%~dp0..\artifacts\singer-full-export\cache"
if not exist "%SINGER_CACHE%\export-manifest.json" (
echo 请先使用歌词导出入口生成成功缓存，或指定 --cache-dir 和 --output-dir。
pause
exit /b 2
)
python "%SINGER_TOOL%" --cache-dir "%SINGER_CACHE%" --output-dir "%SINGER_CACHE%\..\singer-preview" --manual-dir "%SINGER_CACHE%\..\manual-singers"
set "SINGER_RESULT=%errorlevel%"
echo 歌手标记生成结束，已有人工修订保持独立。
pause
exit /b %SINGER_RESULT%

:arguments
python "%SINGER_TOOL%" %*
exit /b %errorlevel%
