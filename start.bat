@echo off
title Streak Maintainer

cd /d "D:\Download\Streak_Maintainer-main"

echo =====================================
echo Starting Streak Maintainer...
echo =====================================

echo.
echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Generating today's questions (if needed)...
cd backend
python manage.py generate_questions

echo.
echo Starting Django Backend...
start "Backend" cmd /k "cd /d D:\Download\Streak_Maintainer-main\backend && call ..\venv\Scripts\activate && python manage.py runserver"

timeout /t 5 >nul

echo.
echo Starting React Frontend...
start "Frontend" cmd /k "cd /d D:\Download\Streak_Maintainer-main\frontend && npm start"

timeout /t 8 >nul

start http://localhost:3000

exit