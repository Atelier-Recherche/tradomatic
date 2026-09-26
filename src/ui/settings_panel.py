"""
Panneau de configuration des paramètres.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QPushButton, QSpinBox, QFileDialog,
    QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt

from ..utils.i18n import get_i18n
from ..utils.config import get_secure_storage
from ..core.project import Project

logger = logging.getLogger(__name__)


class SettingsPanel(QWidget):
    """
    Panneau de configuration des paramètres de traduction.
    """
    
    def __init__(self, parent=None):
        """Initialise le panneau."""
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self.secure_storage = get_secure_storage()
        self.parent_window = parent
        
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout()
        
        # 1. Configuration API
        api_group = self.create_api_group()
        layout.addWidget(api_group)
        
        # 2. Paramètres de traduction
        translation_group = self.create_translation_group()
        layout.addWidget(translation_group)
        
        # 3. Chemins
        paths_group = self.create_paths_group()
        layout.addWidget(paths_group)
        
        # 4. Paramètres avancés
        advanced_group = self.create_advanced_group()
        layout.addWidget(advanced_group)
        
        # Espaceur
        layout.addStretch()
        
        self.setLayout(layout)
    
    def create_api_group(self) -> QGroupBox:
        """Crée le groupe de configuration API."""
        group = QGroupBox(self.i18n.t("settings_panel.api_config"))
        layout = QVBoxLayout()
        
        # Provider
        provider_layout = QHBoxLayout()
        provider_label = QLabel(self.i18n.t("settings_panel.api_provider"))
        self.api_provider = QComboBox()
        self.api_provider.addItems(["Claude (Anthropic)", "Gemini (Google)"])
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.api_provider)
        layout.addLayout(provider_layout)
        
        # API Key
        key_layout = QHBoxLayout()
        key_label = QLabel(self.i18n.t("settings_panel.api_key"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.api_key_input)
        layout.addLayout(key_layout)
        
        # Model selector (sera rempli après scan)
        model_layout = QHBoxLayout()
        model_label = QLabel("Modèle :")
        self.model_selector = QComboBox()
        self.model_selector.setEnabled(False)
        self.model_selector.addItem("Tester la connexion pour voir les modèles")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_selector)
        layout.addLayout(model_layout)
        
        # Test button
        self.test_api_btn = QPushButton(self.i18n.t("settings_panel.test_connection"))
        self.test_api_btn.clicked.connect(self.test_api_connection)
        layout.addWidget(self.test_api_btn)
        
        group.setLayout(layout)
        return group
    
    def create_translation_group(self) -> QGroupBox:
        """Crée le groupe des paramètres de traduction."""
        group = QGroupBox(self.i18n.t("settings_panel.translation_settings"))
        layout = QVBoxLayout()
        
        # Note explicative
        note_label = QLabel(
            "<i>ℹ️ Ces paramètres contrôlent la logique de traduction "
            "(fréquence des consolidations, résumés, etc.). "
            "Pour modifier le contenu des prompts, allez dans l'onglet Prompts.</i>"
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(note_label)
        
        # Consolidation frequency
        consol_layout = QHBoxLayout()
        consol_label = QLabel(self.i18n.t("settings_panel.consolidation_freq"))
        self.consolidation_freq = QSpinBox()
        self.consolidation_freq.setRange(10, 200)
        self.consolidation_freq.setValue(50)
        self.consolidation_freq.setSuffix(" pages")
        consol_layout.addWidget(consol_label)
        consol_layout.addWidget(self.consolidation_freq)
        layout.addLayout(consol_layout)
        
        # Summary frequency
        summary_layout = QHBoxLayout()
        summary_label = QLabel(self.i18n.t("settings_panel.summary_freq"))
        self.summary_freq = QSpinBox()
        self.summary_freq.setRange(5, 50)
        self.summary_freq.setValue(10)
        self.summary_freq.setSuffix(" pages")
        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(self.summary_freq)
        layout.addLayout(summary_layout)
        
        # Context window
        context_layout = QHBoxLayout()
        context_label = QLabel(self.i18n.t("settings_panel.context_window"))
        self.context_window = QSpinBox()
        self.context_window.setRange(3, 10)
        self.context_window.setValue(5)
        self.context_window.setSuffix(" résumés")
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_window)
        layout.addLayout(context_layout)

        # Langue source
        source_lang_layout = QHBoxLayout()
        source_lang_label = QLabel(self.i18n.t("settings_panel.source_language"))
        self.source_language = QComboBox()
        self.source_language.setEditable(True)
        self.source_language.addItems([
            "allemand", "francais", "italien", "anglais", "espagnol", "portugais"
        ])
        source_lang_layout.addWidget(source_lang_label)
        source_lang_layout.addWidget(self.source_language)
        layout.addLayout(source_lang_layout)

        # Langue cible
        target_lang_layout = QHBoxLayout()
        target_lang_label = QLabel(self.i18n.t("settings_panel.target_language"))
        self.target_language = QComboBox()
        self.target_language.setEditable(True)
        self.target_language.addItems([
            "francais", "allemand", "italien", "anglais", "espagnol", "portugais"
        ])
        target_lang_layout.addWidget(target_lang_label)
        target_lang_layout.addWidget(self.target_language)
        layout.addLayout(target_lang_layout)

        # Activation du glossaire
        self.use_glossary = QCheckBox(self.i18n.t("settings_panel.use_glossary"))
        self.use_glossary.setChecked(True)
        layout.addWidget(self.use_glossary)
        
        group.setLayout(layout)
        return group
    
    def create_paths_group(self) -> QGroupBox:
        """Crée le groupe des chemins de fichiers."""
        group = QGroupBox(self.i18n.t("settings_panel.paths"))
        layout = QVBoxLayout()
        
        # Input directory
        input_layout = QHBoxLayout()
        input_label = QLabel(self.i18n.t("settings_panel.input_dir"))
        self.input_dir = QLineEdit()
        self.input_dir.setPlaceholderText("D:/Documents/input_pages")
        self.input_browse = QPushButton(self.i18n.t("buttons.browse"))
        self.input_browse.clicked.connect(self.browse_input_dir)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_dir)
        input_layout.addWidget(self.input_browse)
        layout.addLayout(input_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel(self.i18n.t("settings_panel.output_dir"))
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("D:/Documents/output")
        self.output_browse = QPushButton(self.i18n.t("buttons.browse"))
        self.output_browse.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(self.output_browse)
        layout.addLayout(output_layout)
        
        group.setLayout(layout)
        return group
    
    def create_advanced_group(self) -> QGroupBox:
        """Crée le groupe des paramètres avancés."""
        group = QGroupBox(self.i18n.t("settings_panel.advanced"))
        layout = QVBoxLayout()
        
        # Rate limit
        rate_layout = QHBoxLayout()
        rate_label = QLabel(self.i18n.t("settings_panel.rate_limit"))
        self.rate_limit = QSpinBox()
        self.rate_limit.setRange(1, 120)
        self.rate_limit.setValue(60)
        self.rate_limit.setSuffix(" req/min")
        rate_layout.addWidget(rate_label)
        rate_layout.addWidget(self.rate_limit)
        layout.addLayout(rate_layout)
        
        # Retry max
        retry_layout = QHBoxLayout()
        retry_label = QLabel(self.i18n.t("settings_panel.retry_max"))
        self.retry_max = QSpinBox()
        self.retry_max.setRange(1, 10)
        self.retry_max.setValue(3)
        retry_layout.addWidget(retry_label)
        retry_layout.addWidget(self.retry_max)
        layout.addLayout(retry_layout)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel(self.i18n.t("settings_panel.timeout"))
        self.timeout = QSpinBox()
        self.timeout.setRange(30, 300)
        self.timeout.setValue(120)
        self.timeout.setSuffix(" s")
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout)
        layout.addLayout(timeout_layout)
        
        # Checkpoint frequency
        checkpoint_layout = QHBoxLayout()
        checkpoint_label = QLabel(self.i18n.t("settings_panel.checkpoint_freq"))
        self.checkpoint_freq = QSpinBox()
        self.checkpoint_freq.setRange(5, 50)
        self.checkpoint_freq.setValue(10)
        self.checkpoint_freq.setSuffix(" pages")
        checkpoint_layout.addWidget(checkpoint_label)
        checkpoint_layout.addWidget(self.checkpoint_freq)
        layout.addLayout(checkpoint_layout)
        
        group.setLayout(layout)
        return group
    
    def browse_input_dir(self):
        """Ouvre le dialogue de sélection du dossier d'entrée."""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.i18n.t("messages.select_input_dir"),
            self.input_dir.text()
        )
        
        if directory:
            self.input_dir.setText(directory)
    
    def browse_output_dir(self):
        """Ouvre le dialogue de sélection du dossier de sortie."""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.i18n.t("messages.select_output_dir"),
            self.output_dir.text()
        )
        
        if directory:
            self.output_dir.setText(directory)
    
    def test_api_connection(self):
        """Teste la connexion à l'API et charge les modèles disponibles dynamiquement."""
        provider_text = self.api_provider.currentText()
        api_key = self.api_key_input.text()
        
        if not api_key:
            QMessageBox.warning(
                self,
                self.i18n.t("dialogs.warning"),
                self.i18n.t("messages.invalid_api_key")
            )
            return
        
        try:
            # Lister les modèles disponibles via l'API (inclut Gemma pour Google)
            if "Claude" in provider_text:
                from ..core.claude_api import ClaudeAPI, list_claude_models
                available_models = list_claude_models(api_key)
                # Utiliser le premier modèle pour le test
                test_model = available_models[0][0] if available_models else "claude-sonnet-4-20250514"
                api = ClaudeAPI(api_key, model=test_model)
            else:
                from ..core.gemini_api import GeminiAPI, list_gemini_models
                available_models = list_gemini_models(api_key)
                # Utiliser le premier modèle pour le test
                test_model = available_models[0][0] if available_models else "gemini-1.5-flash"
                api = GeminiAPI(api_key, model=test_model)
            
            # Vérifier qu'on a des modèles
            if not available_models:
                QMessageBox.critical(
                    self,
                    self.i18n.t("dialogs.error"),
                    "Aucun modèle disponible pour ce fournisseur"
                )
                return
            
            # Tester la connexion
            if api.test_connection():
                # Remplir le sélecteur de modèles
                self.model_selector.clear()
                for model_id, display_name in available_models:
                    self.model_selector.addItem(display_name, model_id)
                self.model_selector.setEnabled(True)
                
                # Pré-sélectionner le modèle sauvegardé si présent
                if self.parent_window and self.parent_window.current_project:
                    saved_model = self.parent_window.current_project.api_settings.get("model", "")
                    for i in range(self.model_selector.count()):
                        if self.model_selector.itemData(i) == saved_model:
                            self.model_selector.setCurrentIndex(i)
                            break
                
                QMessageBox.information(
                    self,
                    self.i18n.t("dialogs.success"),
                    f"{self.i18n.t('messages.api_test_success')}\n\n"
                    f"Modèles disponibles : {len(available_models)} (inclut Gemma pour Google)"
                )
            else:
                QMessageBox.critical(
                    self,
                    self.i18n.t("dialogs.error"),
                    self.i18n.t("messages.api_test_failed")
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                self.i18n.t("dialogs.error"),
                f"{self.i18n.t('messages.api_test_failed')}:\n{str(e)}"
            )
            logger.error(f"Test API échoué: {e}")
    
    def load_from_project(self, project: Project):
        """
        Charge les paramètres depuis un projet.
        
        Args:
            project: Instance de Project
        """
        # API settings
        provider = project.api_settings.get("provider", "gemini")
        if provider == "claude":
            self.api_provider.setCurrentIndex(0)
        else:
            self.api_provider.setCurrentIndex(1)
        
        # Déchiffrer la clé API
        encrypted_key = project.api_settings.get("api_key_encrypted", "")
        if encrypted_key:
            api_key = self.secure_storage.decrypt_api_key(encrypted_key)
            self.api_key_input.setText(api_key)
        
        self.rate_limit.setValue(project.api_settings.get("rate_limit", 60))
        self.retry_max.setValue(project.api_settings.get("retry_max", 3))
        self.timeout.setValue(project.api_settings.get("timeout", 120))
        
        # Réinitialiser le sélecteur de modèles (il faudra retester pour charger)
        self.model_selector.clear()
        self.model_selector.addItem("Tester la connexion pour voir les modèles")
        self.model_selector.setEnabled(False)
        
        # Translation settings
        self.consolidation_freq.setValue(
            project.translation_settings.get("consolidation_frequency", 50)
        )
        self.summary_freq.setValue(
            project.translation_settings.get("summary_frequency", 10)
        )
        self.context_window.setValue(
            project.translation_settings.get("context_window_size", 5)
        )
        self.checkpoint_freq.setValue(
            project.translation_settings.get("checkpoint_frequency", 10)
        )
        source_language = project.translation_settings.get("source_language", "allemand")
        target_language = project.translation_settings.get("target_language", "francais")
        use_glossary = project.translation_settings.get("use_glossary", True)

        self.source_language.setCurrentText(source_language)
        self.target_language.setCurrentText(target_language)
        self.use_glossary.setChecked(use_glossary)
        
        # Paths
        input_path = project.paths.get("input_directory", "")
        output_path = project.paths.get("output_directory", "")
        
        self.input_dir.setText(input_path)
        self.output_dir.setText(output_path)
        
        logger.info(f"Chemins chargés - Entrée: '{input_path}', Sortie: '{output_path}'")
        logger.debug("Paramètres chargés depuis le projet")
    
    def save_to_project(self, project: Project):
        """
        Sauvegarde les paramètres dans un projet.
        
        Args:
            project: Instance de Project
        """
        # API settings
        provider_text = self.api_provider.currentText()
        provider = "claude" if "Claude" in provider_text else "gemini"
        
        # Chiffrer la clé API
        api_key = self.api_key_input.text()
        encrypted_key = self.secure_storage.encrypt_api_key(api_key) if api_key else ""
        
        # Récupérer le model_id sélectionné (userData du combo)
        model_id = self.model_selector.currentData()
        if not model_id and self.model_selector.count() > 0:
            # Fallback : extraire du texte affiché si pas de userData
            model_id = project.api_settings.get("model", "")
        
        project.api_settings = {
            "provider": provider,
            "api_key_encrypted": encrypted_key,
            "model": model_id or "",
            "rate_limit": self.rate_limit.value(),
            "retry_max": self.retry_max.value(),
            "timeout": self.timeout.value()
        }
        
        # Translation settings
        project.translation_settings = {
            "consolidation_frequency": self.consolidation_freq.value(),
            "summary_frequency": self.summary_freq.value(),
            "context_window_size": self.context_window.value(),
            "checkpoint_frequency": self.checkpoint_freq.value(),
            "source_language": self.source_language.currentText().strip() or "source",
            "target_language": self.target_language.currentText().strip() or "cible",
            "use_glossary": self.use_glossary.isChecked()
        }
        
        # Paths
        project.paths = {
            "input_directory": self.input_dir.text(),
            "output_directory": self.output_dir.text(),
            "glossary_db": f"{self.output_dir.text()}/glossaire.db",
            "logs_directory": "logs"
        }
        
        logger.debug("Paramètres sauvegardés dans le projet")
