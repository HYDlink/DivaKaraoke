@echo off
chcp 65001 >nul
setlocal
set "SINGER_ROOT=%~dp0.."
set "SINGER_OUTPUT=%SINGER_ROOT%\artifacts\exported-lyrics"
if not exist "%SINGER_OUTPUT%\cache\export-manifest.json" set "SINGER_OUTPUT=%SINGER_ROOT%\artifacts\singer-full-export"
set "SINGER_INSTALL=%SINGER_ROOT%\lyrics"
if not exist "%SINGER_ROOT%\MMFreeLyrics.dll" set "SINGER_INSTALL=E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods\MMFreeLyrics\lyrics"
if not exist "%SINGER_OUTPUT%\cache\export-manifest.json" goto missing
if not "%~1"=="" goto custom
rem 仅重新应用歌手标记，人工文件保持独立，安装前仍预检所有歌词和旁路哈希。
python "%SINGER_ROOT%\scripts\export_lyrics.py" --output-dir "%SINGER_OUTPUT%" --rebuild-singers-only --install-dir "%SINGER_INSTALL%"
goto done
:custom
python "%SINGER_ROOT%\scripts\export_lyrics.py" %*
goto done
:missing
echo 未找到成功导出缓存，请先运行歌词导出入口。
set "SINGER_RESULT=2"
goto pause_exit
:done
set "SINGER_RESULT=%errorlevel%"
if not "%SINGER_RESULT%"=="0" echo 应用失败，人工文件和旧成功缓存保留，请查看上方提示。
:pause_exit
echo 操作结束，按任意键关闭窗口。
pause >nul
exit /b %SINGER_RESULT%
