@echo off
REM install.bat -- Windows installer for the Husk + USD-Export
REM Deadline submitter HDAs.
REM
REM Locates Houdini's hython.exe, runs install_hda.py, and writes two
REM .hda files to the chosen output directory.
REM
REM Override hython detection by setting HYTHON before running.

setlocal enabledelayedexpansion

set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "INSTALL_PY=%HERE%\install_hda.py"
set "DEFAULT_OUT_DIR=%HERE%\otls"
set "DEFAULT_LABEL=inside repo"
set "SECRETS_AUTHORIZED=0"

set "HDA1=gegenschuss_husk_deadline_submitter.hda"
set "HDA2=gegenschuss_usd_deadline_submitter.hda"

if not exist "%INSTALL_PY%" (
    echo install_hda.py not found next to this script ^(%HERE%^).>&2
    exit /b 1
)

REM Optional install_secrets override.  First non-comment, non-blank
REM line is a local default directory.  Gitignored, never published.
if exist "%HERE%\install_secrets" (
    for /f "usebackq tokens=* eol=#" %%i in ("%HERE%\install_secrets") do (
        if not defined _SECRET_PATH set "_SECRET_PATH=%%i"
    )
    if defined _SECRET_PATH (
        if "!_SECRET_PATH:~-1!"=="\" set "_SECRET_PATH=!_SECRET_PATH:~0,-1!"
        set "DEFAULT_OUT_DIR=!_SECRET_PATH!"
        set "DEFAULT_LABEL=from install_secrets"
        set "SECRETS_AUTHORIZED=1"
    )
)

REM ----- Choose install location -----
echo Where should the HDAs install?
echo.
echo   [1] %DEFAULT_OUT_DIR%\   (default, %DEFAULT_LABEL%)
echo   [2] Custom directory
echo.
set "CHOICE="
set /p "CHOICE=Choice [1]: "
if "%CHOICE%"=="" set "CHOICE=1"

if "%CHOICE%"=="1" (
    set "OUT_DIR=%DEFAULT_OUT_DIR%"
    goto :path_chosen
)
if "%CHOICE%"=="2" (
    set "CUSTOM="
    set /p "CUSTOM=Directory: "
    if "!CUSTOM!"=="" (
        echo Empty path; cancelled.>&2
        exit /b 1
    )
    if "!CUSTOM:~-1!"=="\" set "CUSTOM=!CUSTOM:~0,-1!"
    set "OUT_DIR=!CUSTOM!"
    goto :path_chosen
)
echo Invalid choice.>&2
exit /b 1

:path_chosen
echo "%OUT_DIR%" | findstr /B /L /C:"%HERE%" >nul
if %ERRORLEVEL% NEQ 0 (
    if "%SECRETS_AUTHORIZED%"=="1" if "%CHOICE%"=="1" goto :outside_ok
    echo.
    echo This will create files OUTSIDE the repo:
    echo   %OUT_DIR%\
    set "YN="
    set /p "YN=Proceed? [y/N]: "
    if /I not "!YN!"=="y" if /I not "!YN!"=="yes" (
        echo Cancelled.
        exit /b 0
    )
    :outside_ok
)

REM ----- Replace-existing check -----
set "ANY_EXISTS="
if exist "%OUT_DIR%\%HDA1%" set "ANY_EXISTS=1"
if exist "%OUT_DIR%\%HDA2%" set "ANY_EXISTS=1"
if defined ANY_EXISTS (
    echo.
    echo These files already exist:
    if exist "%OUT_DIR%\%HDA1%" echo   %OUT_DIR%\%HDA1%
    if exist "%OUT_DIR%\%HDA2%" echo   %OUT_DIR%\%HDA2%
    set "YN=y"
    set /p "YN=Replace? [Y/n]: "
    if /I "!YN!"=="n" (echo Cancelled. & exit /b 0)
    if /I "!YN!"=="no" (echo Cancelled. & exit /b 0)
)

REM ----- Find hython.exe -----
if defined HYTHON (
    if exist "%HYTHON%" (
        set "HYTHON_BIN=%HYTHON%"
        goto :found
    )
)
where hython.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    for /f "delims=" %%i in ('where hython.exe') do (
        set "HYTHON_BIN=%%i"
        goto :found
    )
)
set "HYTHON_BIN="
for /d %%d in ("C:\Program Files\Side Effects Software\Houdini *") do (
    if exist "%%d\bin\hython.exe" set "HYTHON_BIN=%%d\bin\hython.exe"
)
if defined HYTHON_BIN goto :found

echo Could not find hython.exe.>&2
echo Set HYTHON to your hython.exe path and re-run.>&2
exit /b 1

:found
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo.
echo hython:    %HYTHON_BIN%
echo script:    %INSTALL_PY%
echo out dir:   %OUT_DIR%
echo.

"%HYTHON_BIN%" "%INSTALL_PY%" "%OUT_DIR%"
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!
endlocal
