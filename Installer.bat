@echo off

REM check if running as admin

goto check_Permissions

:check_Permissions
echo Administrative permissions required. Detecting permissions...

net session >nul 2>&1
if %errorLevel% == 0 (
    goto 1
) else (
    cls
    echo Failure: You MUST run this as administator, otherwise commands will fail. 
)

pause >nul



REM Step 2: Check if Python and pip3 are installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b
)

pip3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo pip3 is not installed. Please install pip3.
    pause
    exit /b
)

REM Step 3: Check Python version
python -c "import sys; exit(0) if sys.version_info >= (3,8) else exit(1)"
if %errorlevel% neq 0 (
    echo Python version 3.8 or higher is required.
    pause
    exit /b
)


:1
cls
:::===============================================================
:::   ______                  __  __       _                _   
:::  |  ____|                |  \/  |     (_)              | |  
:::  | |__   __ _ ___ _   _  | \  / | __ _ _  __ _ _ __ ___| |_ 
:::  |  __| / _` / __| | | | | |\/| |/ _` | |/ _` | '__/ _ \ __|
:::  | |___| (_| \__ \ |_| | | |  | | (_| | | (_| | | |  __/ |_ 
:::  |______\__,_|___/\__, | |_|  |_|\__,_|_|\__, |_|  \___|\__|
:::                    __/ |                  __/ |             
:::                   |___/                  |___/             
:::
:::===============================================================
echo.
for /f "delims=: tokens=*" %%A in ('findstr /b ::: "%~f0"') do @echo(%%A
echo.
echo ----------------------------------------------------------------
echo              Python 3.8 or higher and pip3 required.
echo ----------------------------------------------------------------
echo                 Press [I] to begin installation.
echo                 Press [R] If already installed.
echo ----------------------------------------------------------------
choice /c IR
if %errorlevel%==1 goto install1
if %errorlevel%==2 goto after

:install1
cls
echo ========================================================
echo                Maigret Installation Script
echo ========================================================
echo.
echo --------------------------------------------------------
echo   If your pip installation is outdated, it could cause
echo         cryptography to fail on installation.
echo --------------------------------------------------------
echo          check for and install pip updates now?
echo --------------------------------------------------------
choice /c YN
if %errorlevel%==1 goto install2
if %errorlevel%==2 goto install3

:install2
cls
python -m pip install --upgrade pip
goto:install3

:install3
cls
echo ========================================================
echo                Maigret Installation Script
echo ========================================================
echo.
echo --------------------------------------------------------
echo             Install requirements and maigret?
echo --------------------------------------------------------
choice /c YN
if %errorlevel%==1 goto install4
if %errorlevel%==2 goto 1

:install4
cls
pip install -r requirements.txt
pip install maigret
goto:after

:after
cls
echo ========================================================
echo                Maigret Background Search
echo ========================================================
echo.
echo --------------------------------------------------------
echo              Please Enter Username / Email
echo --------------------------------------------------------
set /p input= 
maigret %input%
echo.
echo.
echo.
echo.
pause
goto:after