@echo off
REM Script to commit and push Vercel fixes to GitHub

echo ===========================================
echo Commit and Push Vercel Fixes to GitHub
echo ===========================================
echo.

REM Check if git is installed
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not found!
    echo Please install Git from: https://git-scm.com/
    pause
    exit /b 1
)

echo [OK] Git found
echo.

REM Show current status
echo Current git status:
echo -------------------------------------------
git status --short
echo -------------------------------------------
echo.

REM Add all changes
echo Adding all changes...
git add .

REM Commit changes
echo.
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" (
    set commit_msg=Fix Vercel deployment configuration
)

git commit -m "%commit_msg%"

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] No changes to commit or commit failed
    echo.
) else (
    echo.
    echo [OK] Changes committed successfully
    echo.
)

REM Push to GitHub
echo Pushing to GitHub...
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed!
    echo Check your GitHub credentials and try again
    echo.
    pause
    exit /b 1
)

echo.
echo ===========================================
echo [SUCCESS] Changes pushed to GitHub!
echo ===========================================
echo.
echo Vercel will automatically deploy your changes.
echo Check your deployment at: https://vercel.com/dashboard
echo.
echo Next steps:
echo 1. Go to Vercel dashboard
echo 2. Wait for deployment to complete
echo 3. Test your API endpoints
echo.

pause
