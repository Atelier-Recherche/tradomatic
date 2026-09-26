"""
Panneau de traduction avec progression, logs et contrôles.
"""

import logging
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar,
    QLabel, QTextBrowser, QCheckBox, QGroupBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ..utils.i18n import get_i18n
from ..utils.config import get_secure_storage
from ..core.translator import Translator
from ..core.glossary import Glossary
from ..core.context_manager import ContextManager

logger = logging.getLogger(__name__)


class TranslationThread(QThread):
    """
    Thread séparé pour exécuter la traduction sans bloquer l'UI.
    """
    
    progress_updated = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str, str)  # level, message
    page_completed = pyqtSignal(int, str, str)  # num, source, translation
    finished_translation = pyqtSignal(dict)  # rapport final
    
    def __init__(self, translator: Translator, input_files: list, output_dir: str):
        """
        Initialise le thread.
        
        Args:
            translator: Instance de Translator
            input_files: Liste des fichiers à traduire
            output_dir: Répertoire de sortie
        """
        super().__init__()
        self.translator = translator
        self.input_files = input_files
        self.output_dir = output_dir
    
    def run(self):
        """Exécute la traduction."""
        try:
            self.translator.run_translation(
                input_files=self.input_files,
                output_dir=self.output_dir,
                progress_callback=self.on_progress,
                log_callback=self.on_log,
                page_completed_callback=self.on_page_completed
            )
            
            # Traduction terminée
            stats = {
                "total_pages": len(self.input_files),
                "glossary_size": self.translator.glossary.get_size() if self.translator.glossary else 0
            }
            self.finished_translation.emit(stats)
            
        except Exception as e:
            self.log_message.emit("error", f"Erreur fatale: {str(e)}")
            logger.error(f"Erreur dans le thread de traduction: {e}", exc_info=True)
    
    def on_progress(self, current: int, total: int):
        """Callback de progression."""
        self.progress_updated.emit(current, total)
    
    def on_log(self, level: str, message: str):
        """Callback de log."""
        self.log_message.emit(level, message)
    
    def on_page_completed(self, num: int, source: str, translation: str):
        """Callback de page complétée."""
        self.page_completed.emit(num, source, translation)


class TranslationPanel(QWidget):
    """
    Panneau de suivi de traduction en temps réel.
    """
    
    def __init__(self, parent=None):
        """Initialise le panneau."""
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self.parent_window = parent
        self.secure_storage = get_secure_storage()
        
        self.translation_thread = None
        self.translator = None
        self.log_file = None
        self.log_file_handler = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout()
        
        # Contrôles
        controls_group = QGroupBox(self.i18n.t("translation_panel.controls"))
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton(self.i18n.t("buttons.start"))
        self.start_btn.clicked.connect(self.start_translation)
        controls_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton(self.i18n.t("buttons.pause"))
        self.pause_btn.clicked.connect(self.pause_translation)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton(self.i18n.t("buttons.stop"))
        self.stop_btn.clicked.connect(self.stop_translation)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Progression
        progress_group = QGroupBox(self.i18n.t("translation_panel.progress"))
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("0 / 0 pages")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Filtres de logs
        filters_layout = QHBoxLayout()
        filters_label = QLabel(self.i18n.t("translation_panel.filter_logs"))
        filters_layout.addWidget(filters_label)
        
        self.filter_info = QCheckBox(self.i18n.t("translation_panel.filter_info"))
        self.filter_info.setChecked(True)
        self.filter_info.stateChanged.connect(self.apply_log_filters)
        filters_layout.addWidget(self.filter_info)
        
        self.filter_warning = QCheckBox(self.i18n.t("translation_panel.filter_warning"))
        self.filter_warning.setChecked(True)
        self.filter_warning.stateChanged.connect(self.apply_log_filters)
        filters_layout.addWidget(self.filter_warning)
        
        self.filter_error = QCheckBox(self.i18n.t("translation_panel.filter_error"))
        self.filter_error.setChecked(True)
        self.filter_error.stateChanged.connect(self.apply_log_filters)
        filters_layout.addWidget(self.filter_error)
        
        self.filter_api = QCheckBox(self.i18n.t("translation_panel.filter_api"))
        self.filter_api.setChecked(True)
        self.filter_api.stateChanged.connect(self.apply_log_filters)
        filters_layout.addWidget(self.filter_api)
        
        filters_layout.addStretch()
        
        layout.addLayout(filters_layout)
        
        # Zone de logs
        self.log_viewer = QTextBrowser()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMinimumHeight(400)
        layout.addWidget(self.log_viewer)
        
        self.setLayout(layout)
    
    def start_translation(self):
        """Démarre la traduction."""
        # Vérifier qu'un projet est ouvert
        if not self.parent_window.current_project:
            QMessageBox.warning(
                self,
                self.i18n.t("dialogs.warning"),
                "Veuillez d'abord créer ou ouvrir un projet"
            )
            return
        
        project = self.parent_window.current_project
        
        # Sauvegarder les paramètres actuels depuis l'UI (modèle, chemins, etc.)
        self.parent_window.settings_panel.save_to_project(project)
        
        # Vérifier qu'un modèle est sélectionné
        if not project.api_settings.get("model"):
            reply = QMessageBox.question(
                self,
                self.i18n.t("dialogs.warning"),
                "Aucun modèle sélectionné. Allez dans Paramètres et cliquez sur "
                "'Tester la connexion' pour charger les modèles disponibles (Gemma, Gemini 3, etc.).\n\n"
                "Voulez-vous continuer avec le modèle par défaut ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            # Utiliser le défaut pour ce provider
            if project.api_settings.get("provider") == "claude":
                project.api_settings["model"] = "claude-sonnet-4-20250514"
            else:
                project.api_settings["model"] = "gemini-1.5-flash"
        
        # Valider le projet
        is_valid, errors = project.validate()
        if not is_valid:
            QMessageBox.critical(
                self,
                self.i18n.t("dialogs.error"),
                "Configuration du projet invalide:\n" + "\n".join(errors)
            )
            return
        
        # Récupérer les fichiers d'entrée
        input_files = project.get_input_files()
        if not input_files:
            QMessageBox.warning(
                self,
                self.i18n.t("dialogs.warning"),
                self.i18n.t("messages.no_input_files")
            )
            return
        
        # Initialiser les composants
        try:
            # API
            provider = project.api_settings["provider"]
            api_key = self.secure_storage.decrypt_api_key(
                project.api_settings["api_key_encrypted"]
            )
            
            model = project.api_settings.get("model") or ""
            
            if provider == "claude":
                from ..core.claude_api import ClaudeAPI
                api = ClaudeAPI(
                    api_key=api_key,
                    model=model or "claude-sonnet-4-20250514",
                    rate_limit=project.api_settings["rate_limit"],
                    timeout=project.api_settings["timeout"]
                )
            else:
                from ..core.gemini_api import GeminiAPI
                api = GeminiAPI(
                    api_key=api_key,
                    model=model or "gemini-1.5-flash",
                    rate_limit=project.api_settings["rate_limit"],
                    timeout=project.api_settings["timeout"]
                )
            
            # Glossaire (optionnel)
            use_glossary = project.translation_settings.get("use_glossary", True)
            glossary = None
            if use_glossary:
                glossary_path = Path(project.paths["output_directory"]) / "glossaire.db"
                glossary = Glossary(str(glossary_path))
                self.parent_window.glossary_panel.set_glossary(glossary)
            else:
                self.parent_window.glossary_panel.set_glossary(None)
                self.parent_window.glossary_panel.clear()
            
            # Contexte
            context_mgr = ContextManager(
                window_size=project.translation_settings["context_window_size"],
                pages_per_summary=project.translation_settings["summary_frequency"]
            )
            
            # Prompts
            prompts = self.parent_window.prompts_panel.get_prompts()
            
            # Translator
            self.translator = Translator(
                api=api,
                glossary=glossary,
                context_mgr=context_mgr,
                prompts=prompts,
                consolidation_freq=project.translation_settings["consolidation_frequency"],
                source_language=project.translation_settings.get("source_language", "source"),
                target_language=project.translation_settings.get("target_language", "cible"),
                use_glossary=use_glossary
            )
            
            # Créer le fichier de log À CÔTÉ du fichier projet
            if self.parent_window.current_project_file:
                project_dir = Path(self.parent_window.current_project_file).parent
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.log_file = project_dir / f"traduction_{timestamp}.log"
            else:
                # Fallback si pas de fichier projet
                log_dir = Path(project.paths.get("output_directory", "logs"))
                log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.log_file = log_dir / f"traduction_{timestamp}.log"
            
            # Ajouter un handler pour rediriger TOUS les logs vers le fichier
            self._setup_log_file_handler()
            
            # Créer et démarrer le thread
            self.translation_thread = TranslationThread(
                translator=self.translator,
                input_files=input_files,
                output_dir=project.paths["output_directory"]
            )
            
            # Connecter les signaux
            self.translation_thread.progress_updated.connect(self.update_progress)
            self.translation_thread.log_message.connect(self.add_log_message)
            self.translation_thread.page_completed.connect(self.on_page_completed)
            self.translation_thread.finished_translation.connect(self.on_translation_finished)
            
            # Démarrer
            self.translation_thread.start()
            
            # Mettre à jour l'UI
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
            self.add_log_message("info", self.i18n.t("messages.translation_started"))
            self.add_log_message("info", f"📄 Log complet: {self.log_file.name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.i18n.t("dialogs.error"),
                f"Erreur lors de l'initialisation:\n{str(e)}"
            )
            logger.error(f"Erreur initialisation traduction: {e}", exc_info=True)
    
    def _setup_log_file_handler(self):
        """Configure un handler pour écrire TOUS les logs dans le fichier."""
        if not self.log_file:
            return
        
        # Créer un handler de fichier
        self.log_file_handler = logging.FileHandler(self.log_file, encoding='utf-8', mode='w')
        self.log_file_handler.setLevel(logging.DEBUG)  # Capturer TOUS les logs
        
        # Format détaillé
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.log_file_handler.setFormatter(formatter)
        
        # FORCER l'ajout du handler au logger racine
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_file_handler)
        root_logger.setLevel(logging.DEBUG)
        
        # Forcer TOUS les loggers existants à propager au root
        for name in logging.root.manager.loggerDict:
            if name.startswith('src.'):
                module_logger = logging.getLogger(name)
                module_logger.setLevel(logging.DEBUG)
                module_logger.propagate = True  # FORCER la propagation
        
        logger.info(f"Handler de log fichier configuré: {self.log_file}")
        logger.info("=" * 80)
        logger.info("DÉBUT DE LA TRADUCTION")
        logger.info("=" * 80)
    
    def _remove_log_file_handler(self):
        """Retire le handler de fichier."""
        if self.log_file_handler:
            logging.getLogger().removeHandler(self.log_file_handler)
            self.log_file_handler.close()
            self.log_file_handler = None
    
    def pause_translation(self):
        """Met en pause ou reprend la traduction."""
        if self.translator:
            if self.translator.is_paused:
                self.translator.resume()
                self.pause_btn.setText(self.i18n.t("buttons.pause"))
                self.add_log_message("info", "Traduction reprise")
            else:
                self.translator.pause()
                self.pause_btn.setText(self.i18n.t("buttons.resume"))
                self.add_log_message("info", self.i18n.t("messages.translation_paused"))
    
    def stop_translation(self):
        """Arrête la traduction."""
        if self.translator:
            reply = QMessageBox.question(
                self,
                self.i18n.t("dialogs.confirm"),
                "Voulez-vous vraiment arrêter la traduction ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.translator.stop()
                self.add_log_message("warning", self.i18n.t("messages.translation_stopped"))
    
    def update_progress(self, current: int, total: int):
        """
        Met à jour la barre de progression.
        
        Args:
            current: Page actuelle
            total: Total de pages
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"{current} / {total} pages")
    
    def add_log_message(self, level: str, message: str):
        """
        Ajoute un message au log.
        
        Args:
            level: Niveau (info, warning, error, api)
            message: Message
        """
        # Couleurs par niveau
        colors = {
            "info": "#d4d4d4",
            "warning": "#FFA500",
            "error": "#FF0000",
            "api": "#569cd6"
        }
        
        color = colors.get(level, "#d4d4d4")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        html = f'<span style="color:{color}">[{timestamp}] [{level.upper()}] {message}</span><br>'
        
        self.log_viewer.append(html)
        
        # Auto-scroll
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Sauvegarder dans le fichier
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
            except Exception as e:
                logger.error(f"Erreur écriture log: {e}")
    
    def on_page_completed(self, num: int, source: str, translation: str):
        """
        Appelé quand une page est complétée.
        
        Args:
            num: Numéro de page
            source: Texte source
            translation: Traduction
        """
        # Mettre à jour le panneau de comparaison
        if hasattr(self.parent_window, 'comparison_panel'):
            self.parent_window.comparison_panel.add_page(num, source, translation)
        
        # Actualiser le panneau glossaire
        if hasattr(self.parent_window, 'glossary_panel'):
            self.parent_window.glossary_panel.refresh_glossary()
    
    def on_translation_finished(self, stats: dict):
        """
        Appelé quand la traduction est terminée.
        
        Args:
            stats: Statistiques de traduction
        """
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        self.add_log_message("info", self.i18n.t("messages.translation_completed"))
        self.add_log_message("info", f"Total pages: {stats.get('total_pages', 0)}")
        if self.translator and self.translator.use_glossary:
            self.add_log_message("info", f"Taille glossaire: {stats.get('glossary_size', 0)} termes")
        else:
            self.add_log_message("info", "Glossaire désactivé pour cette traduction")
        
        # Retirer le handler de log fichier
        self._remove_log_file_handler()
        
        QMessageBox.information(
            self,
            self.i18n.t("dialogs.success"),
            self.i18n.t("messages.translation_completed")
        )
    
    def apply_log_filters(self):
        """Applique les filtres de logs (non implémenté pour simplifier)."""
        # TODO: Implémenter le filtrage réel des logs
        pass
