@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "app\deploy_app.py" (set APP=app\deploy_app.py) else (set APP=deploy_app.py)
where py >nul 2>nul
if %errorlevel%==0 ( py -3 %APP% & goto :fim )
where python >nul 2>nul
if %errorlevel%==0 ( python %APP% & goto :fim )
echo.
echo  Falta instalar o Python (e so se faz uma vez).
echo  Vai abrir a pagina de transferencia. Instale e, no primeiro ecra,
echo  MARQUE a opcao "Add python.exe to PATH". Depois volte a abrir este ficheiro.
echo.
start https://www.python.org/downloads/
:fim
pause
