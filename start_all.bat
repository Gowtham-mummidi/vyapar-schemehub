@echo off
echo ==========================================
echo Starting Vyapar SchemeHub...
echo ==========================================

:: Start backend in a new window
echo Starting FastAPI Backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d "%~dp0backend" && if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe run.py) else (python run.py)"

:: Wait 3 seconds
timeout /t 3 /nobreak >nul

:: Start frontend in a new window
echo Starting React Vite Frontend on port 5173...
start "Vite Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo ==========================================
echo Setup complete. Access urls:
echo  - Frontend: http://localhost:5173
echo  - API Docs: http://localhost:8000/docs
echo ==========================================
pause
