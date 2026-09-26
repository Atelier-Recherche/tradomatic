@echo off
cd /d "%~dp0"

echo Installation des dependances...
pip install -r requirements.txt
pip install pyinstaller>=6.0.0

echo.
echo Build de l'executable...
pyinstaller tradomatic.spec

echo.
if exist "dist\Tradomatic.exe" (
    echo Termine : dist\Tradomatic.exe
) else (
    echo Echec du build. Verifiez les messages ci-dessus.
)
pause
