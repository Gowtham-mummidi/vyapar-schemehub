@echo off
echo ==========================================
echo Deploying Vyapar SchemeHub to Cloud
echo ==========================================
echo Target Platforms:
echo  - Backend:  Render (vyapar-backend)
echo  - Frontend: Vercel (vyapar-schemehub)
echo  - Remote:   https://github.com/Gowtham-mummidi/vyapar-schemehub.git [main]
echo ==========================================

cd /d "%~dp0"

echo [1/3] Staging changes...
git add .

echo [2/3] Committing changes...
git commit -m "Fix admin scheme registration, business profile percentages, and project list sync"

echo [3/3] Pushing to GitHub (triggers Render and Vercel auto-deploy)...
git push origin main

echo ==========================================
if %ERRORLEVEL% EQU 0 (
    echo Deployment triggered successfully!
    echo Monitor your deployments at:
    echo  - Render: https://dashboard.render.com
    echo  - Vercel: https://vercel.com/dashboard
) else (
    echo An error occurred during git push. Please check your network and credentials.
)
echo ==========================================
pause

