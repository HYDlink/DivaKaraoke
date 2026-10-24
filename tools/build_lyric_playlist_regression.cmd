@echo off
if not exist artifacts\lyric-playlist-build mkdir artifacts\lyric-playlist-build
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe" tools\lyric_playlist_regression.vcxproj /nologo /p:Configuration=Release /p:Platform=x64 /v:minimal >artifacts\lyric-playlist-build\regression-build.log 2>&1
if errorlevel 1 exit /b 1
artifacts\lyric-playlist-build\lyric_playlist_regression.exe %*
