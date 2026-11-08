"""
Gestion des projets de traduction (sauvegarde/chargement).
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class Project:
    """
    Représente un projet de traduction avec tous ses paramètres.
    """
    
    VERSION = "1.0"
    
    def __init__(self):
        """Initialise un nouveau projet vide."""
        self.name = "Nouveau projet"
        self.created_at = datetime.now().isoformat()
        self.last_modified = datetime.now().isoformat()
        
        # Chemins
        self.paths = {
            "input_directory": "",
            "output_directory": "",
            "glossary_db": "",
            "logs_directory": ""
        }
        
        # Paramètres API
        self.api_settings = {
            "provider": "gemini",  # ou "claude"
            "api_key_encrypted": "",
            "rate_limit": 60,
            "retry_max": 3,
            "timeout": 120
        }
        
        # Paramètres de traduction
        self.translation_settings = {
            "consolidation_frequency": 50,
            "summary_frequency": 10,
            "context_window_size": 5,
            "checkpoint_frequency": 10,
            "source_language": "allemand",
            "target_language": "francais",
            "use_glossary": True,
            "translation_profile": "custom"
        }
        
        # Prompts personnalisés
        self.prompts = {
            "system_prompt": "",
            "user_prompt": "",
            "consolidation_prompt": "",
            "summary_prompt": ""
        }
        
        # Progression
        self.progress = {
            "current_page": 0,
            "total_pages": 0,
            "last_checkpoint": 0
        }
        
        # Interface
        self.ui_settings = {
            "language": "fr_FR",
            "theme": "dark"
        }
    
    def save(self, filepath: str):
        """
        Sauvegarde le projet en JSON.
        
        Args:
            filepath: Chemin du fichier de sauvegarde
        """
        self.last_modified = datetime.now().isoformat()
        
        data = {
            "version": self.VERSION,
            "project_name": self.name,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "paths": self.paths,
            "api_settings": self.api_settings,
            "translation_settings": self.translation_settings,
            "prompts": self.prompts,
            "progress": self.progress,
            "ui_settings": self.ui_settings
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Projet sauvegardé: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du projet: {e}")
            raise
    
    @staticmethod
    def load(filepath: str) -> 'Project':
        """
        Charge un projet depuis un fichier JSON.
        
        Args:
            filepath: Chemin du fichier à charger
            
        Returns:
            Instance de Project
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            project = Project()
            
            # Vérifier la version
            version = data.get("version", "1.0")
            if version != Project.VERSION:
                logger.warning(f"Version du projet différente: {version} vs {Project.VERSION}")
            
            # Charger les données
            project.name = data.get("project_name", "Projet sans nom")
            project.created_at = data.get("created_at", "")
            project.last_modified = data.get("last_modified", "")
            project.paths = data.get("paths", {})
            project.api_settings = data.get("api_settings", {})
            project.translation_settings = data.get("translation_settings", {})
            project.translation_settings.setdefault("source_language", "allemand")
            project.translation_settings.setdefault("target_language", "francais")
            project.translation_settings.setdefault("use_glossary", True)
            project.translation_settings.setdefault("translation_profile", "custom")
            project.prompts = data.get("prompts", {})
            project.progress = data.get("progress", {})
            project.ui_settings = data.get("ui_settings", {})
            
            logger.info(f"Projet chargé: {filepath}")
            return project
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du projet: {e}")
            raise
    
    def create_checkpoint(self, page_num: int, context_state: Dict, 
                         checkpoint_dir: str = "checkpoints"):
        """
        Crée un checkpoint de l'état actuel.
        
        Args:
            page_num: Numéro de page actuel
            context_state: État du gestionnaire de contexte
            checkpoint_dir: Répertoire des checkpoints
        """
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        self.progress["current_page"] = page_num
        self.progress["last_checkpoint"] = page_num
        
        checkpoint_data = {
            "page_num": page_num,
            "timestamp": datetime.now().isoformat(),
            "project_state": {
                "name": self.name,
                "paths": self.paths,
                "progress": self.progress
            },
            "context_state": context_state
        }
        
        checkpoint_file = checkpoint_path / f"checkpoint_page_{page_num:04d}.json"
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Checkpoint créé: {checkpoint_file}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du checkpoint: {e}")
    
    @staticmethod
    def load_checkpoint(checkpoint_file: str) -> Dict:
        """
        Charge un checkpoint.
        
        Args:
            checkpoint_file: Chemin du fichier checkpoint
            
        Returns:
            Dict avec les données du checkpoint
        """
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Checkpoint chargé: {checkpoint_file}")
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du checkpoint: {e}")
            raise
    
    @staticmethod
    def find_latest_checkpoint(checkpoint_dir: str = "checkpoints") -> Optional[str]:
        """
        Trouve le checkpoint le plus récent.
        
        Args:
            checkpoint_dir: Répertoire des checkpoints
            
        Returns:
            Chemin du checkpoint le plus récent, ou None
        """
        checkpoint_path = Path(checkpoint_dir)
        
        if not checkpoint_path.exists():
            return None
        
        checkpoints = list(checkpoint_path.glob("checkpoint_page_*.json"))
        
        if not checkpoints:
            return None
        
        # Trier par numéro de page (extrait du nom de fichier)
        checkpoints.sort(key=lambda p: int(p.stem.split('_')[-1]))
        
        latest = checkpoints[-1]
        logger.info(f"Checkpoint le plus récent trouvé: {latest}")
        return str(latest)
    
    def get_input_files(self) -> List[str]:
        """
        Retourne la liste des fichiers d'entrée.
        
        Returns:
            Liste des chemins de fichiers markdown
        """
        input_dir = Path(self.paths.get("input_directory", ""))
        
        if not input_dir.exists():
            logger.warning(f"Répertoire d'entrée inexistant: {input_dir}")
            return []
        
        # Rechercher tous les fichiers .md
        files = sorted(input_dir.glob("*.md"))
        
        logger.info(f"Fichiers d'entrée trouvés: {len(files)}")
        return [str(f) for f in files]
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Valide la configuration du projet.
        
        Returns:
            Tuple (is_valid, list_of_errors)
        """
        errors = []
        
        # Vérifier les chemins
        if not self.paths.get("input_directory"):
            errors.append("Répertoire d'entrée non défini")
        elif not Path(self.paths["input_directory"]).exists():
            errors.append("Répertoire d'entrée inexistant")
        
        if not self.paths.get("output_directory"):
            errors.append("Répertoire de sortie non défini")
        
        # Vérifier les paramètres API
        if not self.api_settings.get("provider"):
            errors.append("Fournisseur API non défini")
        
        if not self.api_settings.get("api_key_encrypted"):
            errors.append("Clé API non définie")
        
        # Vérifier les prompts
        if not self.prompts.get("system_prompt"):
            errors.append("Prompt système non défini")
        
        if not self.prompts.get("user_prompt"):
            errors.append("Prompt utilisateur non défini")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Validation du projet réussie")
        else:
            logger.warning(f"Validation du projet échouée: {len(errors)} erreur(s)")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    def get_summary(self) -> Dict:
        """
        Retourne un résumé du projet.
        
        Returns:
            Dict avec informations résumées
        """
        input_files = self.get_input_files()
        
        return {
            "name": self.name,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "api_provider": self.api_settings.get("provider", "non défini"),
            "input_files_count": len(input_files),
            "current_page": self.progress.get("current_page", 0),
            "total_pages": self.progress.get("total_pages", len(input_files))
        }
