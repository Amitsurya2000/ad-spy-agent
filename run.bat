@echo off
REM ============================================================
REM  Ad Spy Agent - one-click launcher
REM  Starts the Flask server + an ngrok tunnel in two windows.
REM ============================================================
setlocal
cd /d "%~dp0"

REM --- Load Gemini API key (env var wins, else read .gemini_key file) ---
if "%GEMINI_API_KEY%"=="" (
  if exist ".gemini_key" set /p GEMINI_API_KEY=<.gemini_key
)
if "%GEMINI_API_KEY%"=="" (
  echo [WARN] GEMINI_API_KEY not set - AI clone/rewrite features will be disabled.
  echo        Put your key in a file named  .gemini_key  in this folder.
  echo.
)

REM --- Locate ngrok (PATH first, then the default install folder) ---
set "NGROK=ngrok"
where ngrok >nul 2>&1 || set "NGROK=C:\Users\Amit\ngrok\ngrok.exe"

echo Starting Ad Spy Agent server on http://localhost:4000 ...
start "AdSpy Server" cmd /k "set GEMINI_API_KEY=%GEMINI_API_KEY%&& "%~dp0venv\Scripts\python.exe" "%~dp0start.py""

echo Waiting for the server to boot...
timeout /t 5 /nobreak >nul

echo Starting ngrok tunnel ...
start "ngrok tunnel" cmd /k ""%NGROK%" http 4000"

echo.
echo ============================================================
echo  Both started in separate windows.
echo  Local:  http://localhost:4000
echo  Public: see the "Forwarding" line in the ngrok window
echo          (or open http://localhost:4040 for the ngrok UI)
echo ============================================================
endlocal
