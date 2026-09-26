@echo off
echo ========================================
echo Installation de Tradomatic
echo ========================================
echo.

echo Creation de l'environnement virtuel...
python -m venv venv
if errorlevel 1 (
    echo ERREUR: Impossible de creer l'environnement virtuel
    pause
    exit /b 1
)

echo.
echo Activation de l'environnement virtuel...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERREUR: Impossible d'activer l'environnement virtuel
    pause
    exit /b 1
)

echo.
echo Installation des dependances...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR: Impossible d'installer les dependances
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation terminee avec succes !
echo ========================================
echo.
echo Pour lancer l'application :
echo   1. Activez l'environnement : venv\Scripts\activate
echo   2. Lancez l'application : python src\main.py
echo.
pause
