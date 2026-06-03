@echo off
REM ----------------------------------------------------------------------
REM run_daily.bat  (para Windows)
REM
REM Ejecuta el rastreador una vez. Pensado para el Programador de tareas
REM (Task Scheduler). Activa el entorno virtual si existe y corre main.py.
REM ----------------------------------------------------------------------

REM Carpeta del proyecto = carpeta padre de este script.
cd /d "%~dp0\.."

REM Si existe un entorno virtual ".venv", lo activamos.
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

if not exist "output" mkdir "output"

REM Ejecuta el rastreador y guarda un log con la fecha (formato YYYY-MM-DD).
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set today=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%
python main.py >> "output\cron-%today%.log" 2>&1
