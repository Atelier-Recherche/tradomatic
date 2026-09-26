@echo off
echo ========================================
echo Lancement de Tradomatic
echo ========================================
echo.

REM Vérifier si l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo ERREUR: Environnement virtuel non trouve
    echo Veuillez d'abord executer install.bat
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
call venv\Scripts\activate

REM Lancer l'application
python src\main.py

REM Désactiver l'environnement virtuel
deactivate

pause
