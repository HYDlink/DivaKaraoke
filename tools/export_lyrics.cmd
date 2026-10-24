@echo off
chcp 65001 >nul
setlocal
rem 默认只复用已有解包资料，在项目工作区生成歌词；不会安装或解包。
if not "%~1"=="" goto custom
echo 正在复用已有来源生成歌词、注音与全部多身份PV的歌手标记。
python "%~dp0..\scripts\export_lyrics.py" --game-dir "E:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus" --output-dir "%~dp0..\artifacts\exported-lyrics"
goto done
:custom
rem 自定义参数原样交给中文帮助的 Python 入口。
python "%~dp0..\scripts\export_lyrics.py" %*
:done
set "export_result=%errorlevel%"
if not "%export_result%"=="0" echo 导出失败，请查看上方中文提示及工作区报告。
echo 操作完成，按任意键关闭窗口。
pause >nul
exit /b %export_result%
