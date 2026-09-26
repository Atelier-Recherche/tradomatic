"""
Gestion de la configuration et du chiffrement des clés API.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)


class SecureStorage:
    """
    Stockage sécurisé pour les clés API.
    """
    
    def __init__(self, key_file: str = ".tradomatic_key"):
        """
        Initialise le stockage sécurisé.
        
        Args:
            key_file: Fichier contenant la clé de chiffrement
        """
        self.key_file = Path.home() / key_file
        self.cipher = self._get_or_create_cipher()
    
    def _get_or_create_cipher(self) -> Fernet:
        """
        Récupère ou crée la clé de chiffrement.
        
        Returns:
            Instance Fernet pour chiffrement
        """
        if self.key_file.exists():
            # Charger la clé existante
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.debug("Clé de chiffrement chargée")
        else:
            # Générer une nouvelle clé
            key = Fernet.generate_key()
            
            # Sauvegarder la clé
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Permissions restrictives (Unix uniquement)
            if os.name != 'nt':  # Pas Windows
                os.chmod(self.key_file, 0o600)
            
            logger.info(f"Nouvelle clé de chiffrement générée: {self.key_file}")
        
        return Fernet(key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Chiffre une clé API.
        
        Args:
            api_key: Clé API en clair
            
        Returns:
            str: Clé API chiffrée (base64)
        """
        if not api_key:
            return ""
        
        encrypted = self.cipher.encrypt(api_key.encode())
        return encrypted.decode()
    
    def decrypt_api_key(self, encrypted: str) -> str:
        """
        Déchiffre une clé API.
        
        Args:
            encrypted: Clé API chiffrée
            
        Returns:
            str: Clé API en clair
        """
        if not encrypted:
            return ""
        
        try:
            decrypted = self.cipher.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement: {e}")
            return ""
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Crée un hash de la clé API (pour vérification).
        
        Args:
            api_key: Clé API
            
        Returns:
            str: Hash SHA256 de la clé
        """
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]


class Config:
    """
    Configuration globale de l'application.
    """
    
    # Valeurs par défaut
    DEFAULTS = {
        "api": {
            "provider": "gemini",
            "rate_limit": 60,
            "retry_max": 3,
            "timeout": 120
        },
        "translation": {
            "consolidation_frequency": 50,
            "summary_frequency": 10,
            "context_window_size": 5,
            "checkpoint_frequency": 10
        },
        "ui": {
            "language": "fr_FR",
            "theme": "dark"
        },
        "paths": {
            "logs_dir": "logs",
            "checkpoints_dir": "checkpoints",
            "templates_dir": "templates"
        }
    }
    
    def __init__(self):
        """Initialise la configuration avec les valeurs par défaut."""
        self.data = self._deep_copy(self.DEFAULTS)
    
    def _deep_copy(self, d: dict) -> dict:
        """Copie profonde d'un dictionnaire."""
        return {k: self._deep_copy(v) if isinstance(v, dict) else v 
                for k, v in d.items()}
    
    def get(self, key: str, default=None):
        """
        Récupère une valeur de configuration.
        
        Args:
            key: Clé avec notation pointée (ex: 'api.provider')
            default: Valeur par défaut
            
        Returns:
            Valeur de configuration
        """
        keys = key.split('.')
        value = self.data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """
        Définit une valeur de configuration.
        
        Args:
            key: Clé avec notation pointée
            value: Nouvelle valeur
        """
        keys = key.split('.')
        d = self.data
        
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        
        d[keys[-1]] = value
    
    def reset_to_defaults(self):
        """Réinitialise la configuration aux valeurs par défaut."""
        self.data = self._deep_copy(self.DEFAULTS)
        logger.info("Configuration réinitialisée aux valeurs par défaut")


# Instance globale
_config_instance = None
_secure_storage_instance = None


def get_config() -> Config:
    """
    Retourne l'instance globale de configuration.
    
    Returns:
        Instance Config
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config()
    
    return _config_instance


def get_secure_storage() -> SecureStorage:
    """
    Retourne l'instance globale de stockage sécurisé.
    
    Returns:
        Instance SecureStorage
    """
    global _secure_storage_instance
    
    if _secure_storage_instance is None:
        _secure_storage_instance = SecureStorage()
    
    return _secure_storage_instance
