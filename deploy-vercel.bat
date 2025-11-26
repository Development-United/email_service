@echo off
REM Quick Vercel Deployment Script for Windows

echo ===========================================
echo Email Service - Vercel Deployment Script
echo ===========================================
echo.

REM Check if vercel CLI is installed
where vercel >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Vercel CLI not found!
    echo.
    echo Install it with: npm install -g vercel
    echo.
    pause
    exit /b 1
)

echo [OK] Vercel CLI found
echo.

REM Check if logged in
vercel whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo Logging into Vercel...
    vercel login
)

echo [OK] Logged into Vercel
echo.

REM Deploy
echo ===========================================
echo Starting deployment...
echo ===========================================
echo.

echo Select deployment type:
echo 1) Preview deployment (for testing)
echo 2) Production deployment
echo.
set /p choice="Enter choice (1 or 2): "

if "%choice%"=="1" (
    echo Deploying to preview...
    vercel
) else if "%choice%"=="2" (
    echo Deploying to production...
    vercel --prod
) else (
    echo Invalid choice. Deploying to preview by default...
    vercel
)

echo.
echo ===========================================
echo Deployment complete!
echo ===========================================
echo.
echo Next steps:
echo 1. Test your deployment URL
echo 2. Check health endpoint: [URL]/health
echo 3. View API docs: [URL]/docs
echo 4. Test email: POST [URL]/api/v1/send-email
echo.

pause
