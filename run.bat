@echo off
echo ====================================
echo   Bot de Registro de Gastos
echo ====================================
echo.
echo Iniciando bot...
echo.

python bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================
    echo   Error al iniciar el bot
    echo ====================================
    echo.
    echo Verifica que:
    echo 1. Has instalado las dependencias: pip install -r requirements.txt
    echo 2. Has configurado el archivo .env correctamente
    echo 3. Has ejecutado el script SQL en Supabase
    echo.
    pause
)
