@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0.."
if not "%~1"=="" goto custom
python scripts\run_local_tools.py singers
set "DIVA_RESULT=%errorlevel%"
goto done
:custom
python scripts\build_singer_timeline.py %*
set "DIVA_RESULT=%errorlevel%"
:done
if not "%DIVA_RESULT%"=="0" echo 工具未完成，请检查本地配置和上方提示。
popd
exit /b %DIVA_RESULT%
