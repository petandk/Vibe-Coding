@echo off@echo off

echo 🚀 Building Flipper Zero Key Spammer...REM Simple Key Spammer Build Script using uFBT

REM No need for full firmware development environment!

REM Check if uFBT is installed

ufbt --version >nul 2>&1echo === Simple Flipper Zero Key Spammer Build ===

if %errorlevel% neq 0 (

    echo ❌ uFBT not found. Please install it first:REM Check if uFBT is installed

    echo    pip3 install --upgrade ufbtwhere /q ufbt

    echo    ufbt updateif %errorlevel% neq 0 (

    pause    echo Installing uFBT...

    exit /b 1    pip install --upgrade ufbt

)    if %errorlevel% neq 0 (

        echo Error: Failed to install uFBT. Make sure Python and pip are installed.

REM Navigate to source directory        echo Visit: https://pypi.org/project/ufbt/

cd src        pause

        exit /b 1

REM Clean previous build    )

echo 🧹 Cleaning previous build...)

ufbt clean

REM Update uFBT to latest SDK

REM Build the applicationecho Updating uFBT SDK...

echo 🔨 Building application...ufbt update

ufbt

REM Navigate to key_spammer directory

if %errorlevel% equ 0 (cd /d key_spammer

    echo ✅ Build successful!

    echo 📦 Output file: dist/key_spammer.fapREM Build the application

    echo 🔧 To install: ufbt launchecho Building key_spammer.fap...

) else (ufbt

    echo ❌ Build failed!

    pauseif %errorlevel% equ 0 (

    exit /b 1    echo.

)    echo === Build successful! ===

    echo Your .fap file is ready in: dist\key_spammer.fap

pause    echo.
    echo To install on Flipper Zero:
    echo 1. Copy dist\key_spammer.fap to your SD card's /ext/apps/ folder
    echo 2. Or use: ufbt launch (to build and install via USB)
    echo.
) else (
    echo === Build failed! ===
    echo Check the error messages above.
)

pause