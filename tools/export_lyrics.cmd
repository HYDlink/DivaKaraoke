@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0.."
if not "%~1"=="" goto custom
echo 请填写本机游戏目录。官方包需先用已有FarcPack提取；详见docs\INSTALL.md。
set /p "DIVA_GAME=游戏目录："
set /p "DIVA_EXTRACTED=已提取官方资料根目录："
python scripts\export_lyrics.py --game-dir "%DIVA_GAME%" --extracted-root "%DIVA_EXTRACTED%" --output-dir artifacts\exported-lyrics
goto done
:custom
python scripts\export_lyrics.py %*
:done
set "DIVA_RESULT=%errorlevel%"
if not "%DIVA_RESULT%"=="0" echo 导出未完成，请查看上方提示。旧成功缓存保持。
popd
exit /b %DIVA_RESULT%
