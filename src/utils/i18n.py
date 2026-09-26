"""
Système d'internationalisation (i18n) pour l'interface.
"""

import json
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class I18n:
    """
    Gestionnaire de traductions pour l'interface multilingue.
    """
    
    AVAILABLE_LANGUAGES = {
        "fr_FR": "Français",
        "en_US": "English"
    }
    
    def __init__(self, language: str = "fr_FR", translations_dir: str = "resources/translations"):
        """
        Initialise le gestionnaire i18n.
        
        Args:
            language: Code de langue (fr_FR, en_US)
            translations_dir: Répertoire contenant les fichiers de traduction
        """
        self.current_language = language
        self.translations_dir = Path(translations_dir)
        self.translations = {}
        
        self.load_translations(language)
    
    def load_translations(self, language: str) -> bool:
        """
        Charge les traductions pour une langue.
        
        Args:
            language: Code de langue
            
        Returns:
            bool: True si chargement réussi
        """
        translation_file = self.translations_dir / f"{language}.json"
        
        if not translation_file.exists():
            logger.error(f"Fichier de traduction introuvable: {translation_file}")
            # Fallback vers français
            if language != "fr_FR":
                logger.warning("Fallback vers fr_FR")
                return self.load_translations("fr_FR")
            return False
        
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            
            self.current_language = language
            logger.info(f"Traductions chargées: {language}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des traductions: {e}")
            return False
    
    def t(self, key: str, default: Optional[str] = None) -> str:
        """
        Traduit une clé.
        
        Args:
            key: Clé de traduction (ex: 'menu.file')
            default: Valeur par défaut si clé introuvable
            
        Returns:
            str: Texte traduit
        """
        keys = key.split('.')
        value = self.translations
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            if default:
                return default
            logger.warning(f"Clé de traduction introuvable: {key}")
            return f"[{key}]"
    
    def change_language(self, language: str) -> bool:
        """
        Change la langue de l'interface.
        
        Args:
            language: Nouveau code de langue
            
        Returns:
            bool: True si changement réussi
        """
        if language not in self.AVAILABLE_LANGUAGES:
            logger.error(f"Langue non disponible: {language}")
            return False
        
        return self.load_translations(language)
    
    def get_current_language(self) -> str:
        """
        Retourne le code de langue actuel.
        
        Returns:
            str: Code de langue
        """
        return self.current_language
    
    def get_current_language_name(self) -> str:
        """
        Retourne le nom de la langue actuelle.
        
        Returns:
            str: Nom de la langue
        """
        return self.AVAILABLE_LANGUAGES.get(self.current_language, "Unknown")
    
    def get_available_languages(self) -> Dict[str, str]:
        """
        Retourne la liste des langues disponibles.
        
        Returns:
            Dict {code: nom}
        """
        return self.AVAILABLE_LANGUAGES.copy()


# Instance globale
_i18n_instance = None


def get_i18n(language: str = "fr_FR") -> I18n:
    """
    Retourne l'instance globale d'i18n (singleton).
    
    Args:
        language: Langue par défaut
        
    Returns:
        Instance I18n
    """
    global _i18n_instance
    
    if _i18n_instance is None:
        _i18n_instance = I18n(language)
    
    return _i18n_instance


def t(key: str, default: Optional[str] = None) -> str:
    """
    Fonction raccourci pour traduire une clé.
    
    Args:
        key: Clé de traduction
        default: Valeur par défaut
        
    Returns:
        str: Texte traduit
    """
    return get_i18n().t(key, default)
