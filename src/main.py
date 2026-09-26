"""
Point d'entrée de l'application Tradomatic.
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.main_window import MainWindow
from src.utils.logger import setup_logging
from src.utils.i18n import get_i18n
from src.utils.config import get_config


def main():
    """Fonction principale."""
    # Configuration du logging
    log_file = setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Démarrage de Tradomatic")
    logger.info(f"Fichier de log: {log_file}")
    logger.info("=" * 60)
    
    # Créer l'application Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Tradomatic")
    app.setOrganizationName("Tradomatic")
    
    try:
        # Charger la configuration
        config = get_config()
        
        # Initialiser i18n
        language = config.get("ui.language", "fr_FR")
        i18n = get_i18n(language)
        logger.info(f"Langue: {i18n.get_current_language_name()}")
        
        # Créer et afficher la fenêtre principale
        window = MainWindow()
        window.show()
        
        logger.info("Interface initialisée")
        
        # Lancer la boucle d'événements
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
