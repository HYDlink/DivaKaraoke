@echo off
rem Build the temporary minimal DLL probe.
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /LD /O2 /utf-8 /Fe:artifacts\mod-load-probe\MMFreeLyricsProbe.dll tools\mod_load_probe.cpp
