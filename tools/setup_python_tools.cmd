@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0.."
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if errorlevel 1 goto missing
if not exist artifacts\setup mkdir artifacts\setup
echo 正在安装歌词工具和OBS助手依赖，不修改系统Python库。
python -m pip --isolated install --disable-pip-version-check --target tools\furigana_runtime Janome==0.5.0 >artifacts\setup\janome.log 2>&1
if errorlevel 1 goto failed
python -m pip --isolated install --disable-pip-version-check --target tools\obs_runtime -r tools\obs-requirements.txt >artifacts\setup\websocket.log 2>&1
if errorlevel 1 goto failed
echo 配套Python依赖已安装。
popd
exit /b 0
:missing
echo 请安装Python 3.11或更新版本，并勾选加入PATH。
popd
exit /b 2
:failed
echo 依赖安装失败，请查看artifacts\setup中的日志。
popd
exit /b 1
