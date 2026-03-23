@echo off
echo ========================================
echo    FinAnalyzer - Smart Financial App
echo ========================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Starting FinAnalyzer application...
echo Open your browser and go to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the application
echo.

python app.py

pause