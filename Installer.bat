@echo off
goto check_Permissions

:check_Permissions
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Success: Elevated permissions granted.
) else (
    echo Failure: Requires elevated permissions.
    pause >nul
)

cls
echo --------------------------------------------------------
echo          Python 3.8 or higher and pip3 required.
echo --------------------------------------------------------
echo             Press [I] to begin installation.
echo             Press [R] If already installed.
echo --------------------------------------------------------
choice /c IR
if %errorlevel%==1 goto check_python
if %errorlevel%==2 goto after

:check_python
cls
for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do (
    for /f "tokens=1,2 delims=." %%j in ("%%i") do (
        if %%j GEQ 3 (
            if %%k GEQ 8 (
                goto check_pip
            )
        )
    )
)
echo Python 3.8 or higher is required. Please install it first.
pause
exit /b

:check_pip
pip --version 2>nul | findstr /r /c:"pip" >nul
if %errorlevel% neq 0 (
    echo pip is required. Please install it first.
    pause
    exit /b
)
goto install1

:install1
cls
echo ========================================================
echo                    Maigret Installation
echo ========================================================
echo.
echo --------------------------------------------------------
echo   If your pip installation is outdated, it could cause
echo         cryptography to fail on installation.
echo --------------------------------------------------------
echo          Check for and install pip 23.3.2 now?
echo --------------------------------------------------------
choice /c YN
if %errorlevel%==1 goto install2
if %errorlevel%==2 goto install3

:install2
cls
python -m pip install --upgrade pip==23.3.2
if %errorlevel% neq 0 (
    echo Failed to update pip to version 23.3.2. Please check your installation.
    pause
    exit /b
)
goto install3

:install3
cls
echo ========================================================
echo                   Maigret Installation
echo ========================================================
echo.
echo --------------------------------------------------------
echo Installing Maigret...
python -m pip install maigret
if %errorlevel% neq 0 (
    echo Failed to install Maigret. Please check your installation.
    pause
    exit /b
)
echo.
echo +------------------------------------------------------+
echo              Maigret installed successfully.           
echo +------------------------------------------------------+
pause
goto after

:after
cls
echo ========================================================
echo                     Maigret Usage
echo ========================================================
echo.
echo +--------------------------------------------------------+
echo To use Maigret, you can run the following command:
echo.
echo     maigret [options] [username]
echo.
echo For example, to search for a username:
echo.
echo     maigret example_username
echo.
echo For more options and usage details, refer to the Maigret documentation.
echo.
echo https://github.com/soxoj/maigret/blob/5b3b81b4822f6deb2e9c31eb95039907f25beb5e/README.md
echo +--------------------------------------------------------+
echo.
cmd
pause
exit /b
exit /b
