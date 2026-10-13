@echo off
chcp 65001 >nul
setlocal
title DIVA OBS 录制助手
rem 使用 UTF-8 编码和 CRLF 换行；中文提示必须在切换代码页后执行。
pushd "%~dp0" >nul 2>&1
if errorlevel 1 goto directory_error
if not exist "%~dp0obs_helper.py" goto helper_missing
rem 优先使用 Python，未找到时尝试 Windows Python 启动器。
python.exe -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>&1
if errorlevel 1 goto try_py
python.exe -u "%~dp0obs_helper.py" %*
goto helper_done
:try_py
py.exe -3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>&1
if errorlevel 1 goto python_missing
py.exe -3 -u "%~dp0obs_helper.py" %*
:helper_done
set "helper_result=%errorlevel%"
if not "%helper_result%"=="0" echo OBS 助手未正常完成，请查看上方中文提示。
popd
echo OBS 助手已结束，按任意键关闭窗口。
pause >nul
exit /b %helper_result%
:python_missing
echo 未找到 Python。请先安装 Python 3 并启用命令行路径，再重新双击此启动器。
set "helper_result=2"
goto launcher_failed
:helper_missing
echo 未找到同目录的 obs_helper.py，请检查模组工具是否安装完整。
set "helper_result=3"
:launcher_failed
popd
echo 启动失败，按任意键关闭窗口。
pause >nul
exit /b %helper_result%
:directory_error
echo 无法进入启动器所在目录，请检查目录是否可访问。
pause >nul
exit /b 4
