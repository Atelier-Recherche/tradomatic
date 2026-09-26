"""
Interface abstraite pour les connecteurs API de traduction.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Décorateur pour retry automatique avec backoff exponentiel.
    
    Args:
        max_attempts: Nombre maximum de tentatives
        backoff_factor: Facteur multiplicateur pour le délai entre tentatives
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = 1.0
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Échec après {max_attempts} tentatives: {str(e)}")
                        raise
                    
                    logger.warning(f"Tentative {attempt}/{max_attempts} échouée: {str(e)}. "
                                 f"Nouvelle tentative dans {delay}s...")
                    time.sleep(delay)
                    delay *= backoff_factor
            
        return wrapper
    return decorator


class APIConnector(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les connecteurs API.
    """
    
    def __init__(self, api_key: str, rate_limit: int = 60, timeout: int = 120):
        """
        Initialise le connecteur API.
        
        Args:
            api_key: Clé API pour l'authentification
            rate_limit: Nombre maximum de requêtes par minute
            timeout: Timeout en secondes pour les requêtes
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.last_request_time = 0
        self.request_count = 0
        
    def _rate_limit_wait(self):
        """Applique le rate limiting en attendant si nécessaire."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Attendre au moins 60/rate_limit secondes entre chaque requête
        min_interval = 60.0 / self.rate_limit
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: attente de {wait_time:.2f}s")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @abstractmethod
    def translate_page(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Traduit une page et retourne JSON avec traduction + termes.
        
        Args:
            system_prompt: Prompt système avec contexte et instructions
            user_prompt: Prompt utilisateur avec le contenu à traduire
            
        Returns:
            Dict contenant:
                - traduction: str - Texte traduit
                - termes_utilises: Dict[str, str] - Termes du glossaire utilisés
                - nouveaux_termes: Dict[str, Dict] - Nouveaux termes proposés
        """
        pass
    
    @abstractmethod
    def consolidate_glossary(self, glossary: Dict[str, str]) -> Dict[str, Any]:
        """
        Consolide le glossaire pour détecter les incohérences.
        
        Args:
            glossary: Dictionnaire des termes actuels {terme_de: terme_fr}
            
        Returns:
            Dict contenant:
                - incohérences_détectées: List[Dict] - Incohérences trouvées
                - glossaire_consolidé: Dict[str, str] - Glossaire harmonisé
        """
        pass
    
    @abstractmethod
    def generate_summary(self, pages: List[str]) -> str:
        """
        Génère un résumé contextuel des pages récentes.
        
        Args:
            pages: Liste des contenus des pages récentes
            
        Returns:
            str: Résumé en ~200 mots
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Teste la connexion à l'API.
        
        Returns:
            bool: True si la connexion fonctionne, False sinon
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques d'utilisation de l'API.
        
        Returns:
            Dict avec nombre de requêtes, etc.
        """
        return {
            "request_count": self.request_count,
            "rate_limit": self.rate_limit
        }
