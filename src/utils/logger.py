"""
Système de logging personnalisé pour la traduction.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class TranslationLogger:
    """
    Logger personnalisé avec callback pour l'interface UI.
    """
    
    def __init__(self, log_file: Optional[str] = None, 
                 callback: Optional[Callable] = None,
                 level: int = logging.INFO):
        """
        Initialise le logger.
        
        Args:
            log_file: Chemin du fichier de log (optionnel)
            callback: Fonction appelée pour chaque log (level, message)
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        """
        self.callback = callback
        self.log_file = log_file
        
        # Créer le logger
        self.logger = logging.getLogger("tradomatic")
        self.logger.setLevel(level)
        
        # Éviter les doublons si déjà configuré
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Format des logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Handler fichier si spécifié
        if log_file:
            # Créer le répertoire si nécessaire
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str):
        """
        Log un message et notifie l'UI via callback.
        
        Args:
            level: Niveau (info, warning, error, debug)
            message: Message à logger
        """
        # Logger dans le système standard
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)
        
        # Notifier l'UI
        if self.callback:
            self.callback(level, message)
    
    def debug(self, message: str):
        """Log niveau DEBUG."""
        self.log("debug", message)
    
    def info(self, message: str):
        """Log niveau INFO."""
        self.log("info", message)
    
    def warning(self, message: str):
        """Log niveau WARNING."""
        self.log("warning", message)
    
    def error(self, message: str):
        """Log niveau ERROR."""
        self.log("error", message)
    
    def api_call(self, message: str):
        """Log spécial pour appels API."""
        self.log("api", message)


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> str:
    """
    Configure le logging global de l'application.
    
    Args:
        log_dir: Répertoire des logs
        level: Niveau de log
        
    Returns:
        str: Chemin du fichier de log créé
    """
    # Créer le répertoire de logs
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Nom du fichier avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"tradomatic_{timestamp}.log"
    
    # Configuration du logger racine
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging initialisé: {log_file}")
    return str(log_file)
