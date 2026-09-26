#!/bin/bash

echo "========================================"
echo "Lancement de Tradomatic"
echo "========================================"
echo

# Vérifier si l'environnement virtuel existe
if [ ! -f "venv/bin/activate" ]; then
    echo "ERREUR: Environnement virtuel non trouvé"
    echo "Veuillez d'abord exécuter: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Lancer l'application
python src/main.py

# Désactiver l'environnement virtuel
deactivate
