"""
Panneau d'édition des prompts avec validation des balises.
"""

import json
import logging
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTextEdit, QPushButton, QTextBrowser, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from ..utils.i18n import get_i18n
from ..core.project import Project

logger = logging.getLogger(__name__)


class PromptHighlighter(QSyntaxHighlighter):
    """
    Coloration syntaxique pour les balises {variable} dans les prompts.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Format pour les balises
        self.tag_format = QTextCharFormat()
        self.tag_format.setForeground(QColor("#569cd6"))  # Bleu
        self.tag_format.setFontWeight(QFont.Weight.Bold)
        
        # Pattern pour détecter les balises {variable}
        self.tag_pattern = re.compile(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}')
    
    def highlightBlock(self, text):
        """Applique la coloration syntaxique."""
        for match in self.tag_pattern.finditer(text):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, self.tag_format)


class PromptsPanel(QWidget):
    """
    Panneau d'édition des templates de prompts.
    """
    
    # Balises disponibles par type de prompt
    AVAILABLE_TAGS = {
        "system_prompt": [
            "{glossaire_json}",
            "{resume_50_dernieres_pages}",
            "{langue_source}",
            "{langue_cible}",
            "{section_glossaire}",
            "{instruction_glossaire}",
            "{instruction_nouveaux_termes}",
            "{format_termes_utilises}",
            "{format_nouveaux_termes}",
            "{note_glossaire}"
        ],
        "user_prompt": [
            "{numero}",
            "{total_pages}",
            "{contenu_markdown_page}"
        ],
        "consolidation_prompt": [
            "{glossaire_recent}"
        ],
        "summary_prompt": [
            "{pages_recentes}"
        ]
    }
    
    def __init__(self, parent=None):
        """Initialise le panneau."""
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self.parent_window = parent
        self.prompts = {}
        self._loading = False  # Flag pour éviter la sauvegarde pendant le chargement initial
        self._current_prompt_key = None  # Garder trace du prompt actuel
        
        self.init_ui()
        self.load_default_prompts()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout()
        
        # Sélecteur de prompt
        selector_layout = QHBoxLayout()
        selector_label = QLabel(self.i18n.t("prompts_panel.select_prompt"))
        self.prompt_selector = QComboBox()
        self.prompt_selector.addItems([
            self.i18n.t("prompts_panel.system_prompt"),
            self.i18n.t("prompts_panel.user_prompt"),
            self.i18n.t("prompts_panel.consolidation_prompt"),
            self.i18n.t("prompts_panel.summary_prompt")
        ])
        self.prompt_selector.currentIndexChanged.connect(self.on_prompt_changed)
        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.prompt_selector)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)
        
        # Éditeur de texte
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Éditez le prompt ici...")
        self.editor.setMinimumHeight(300)
        
        # Appliquer la coloration syntaxique
        self.highlighter = PromptHighlighter(self.editor.document())
        
        layout.addWidget(self.editor)
        
        # Panneau d'aide
        self.help_panel = QTextBrowser()
        self.help_panel.setMaximumHeight(150)
        self.update_help_panel()
        layout.addWidget(self.help_panel)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton(self.i18n.t("buttons.reset"))
        self.reset_btn.clicked.connect(self.reset_current_prompt)
        buttons_layout.addWidget(self.reset_btn)
        
        self.validate_btn = QPushButton("Valider les balises")
        self.validate_btn.clicked.connect(self.validate_tags)
        buttons_layout.addWidget(self.validate_btn)
        
        buttons_layout.addStretch()
        
        self.save_btn = QPushButton(self.i18n.t("buttons.save"))
        self.save_btn.clicked.connect(self.save_current_prompt)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def get_current_prompt_key(self) -> str:
        """Retourne la clé du prompt actuellement sélectionné."""
        index = self.prompt_selector.currentIndex()
        keys = ["system_prompt", "user_prompt", "consolidation_prompt", "summary_prompt"]
        return keys[index]
    
    def on_prompt_changed(self):
        """Appelé quand on change de prompt dans le sélecteur."""
        # Sauvegarder le prompt précédent avant de changer
        if not self._loading and self._current_prompt_key:
            # Sauvegarder le contenu actuel de l'éditeur dans l'ancien prompt
            self.prompts[self._current_prompt_key] = self.editor.toPlainText()
            logger.debug(f"Prompt sauvegardé avant changement: {self._current_prompt_key}")
        
        # Charger le nouveau prompt
        key = self.get_current_prompt_key()
        self._current_prompt_key = key
        content = self.prompts.get(key, "")
        
        # Bloquer les signaux pendant la mise à jour pour éviter les boucles
        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        
        # Mettre à jour l'aide
        self.update_help_panel()
        
        logger.debug(f"Prompt chargé: {key}")
    
    def update_help_panel(self):
        """Met à jour le panneau d'aide avec les balises disponibles."""
        key = self.get_current_prompt_key()
        tags = self.AVAILABLE_TAGS.get(key, [])
        
        html = f"<h4>{self.i18n.t('prompts_panel.help_title')}</h4><ul>"
        
        tag_descriptions = {
            "{glossaire_json}": "Glossaire complet au format JSON",
            "{resume_50_dernieres_pages}": "Résumé contextuel des dernières pages",
            "{langue_source}": "Langue d'entrée choisie dans les paramètres",
            "{langue_cible}": "Langue de sortie choisie dans les paramètres",
            "{section_glossaire}": "Bloc glossaire injecté automatiquement si activé",
            "{instruction_glossaire}": "Instruction terminologique adaptée selon activation du glossaire",
            "{instruction_nouveaux_termes}": "Instruction des nouveaux termes adaptée automatiquement",
            "{format_termes_utilises}": "Exemple JSON du champ termes_utilises (ou {} si glossaire off)",
            "{format_nouveaux_termes}": "Exemple JSON du champ nouveaux_termes (ou {} si glossaire off)",
            "{note_glossaire}": "Notes finales liées au comportement du glossaire",
            "{numero}": "Numéro de la page actuelle",
            "{total_pages}": "Nombre total de pages",
            "{contenu_markdown_page}": "Contenu source de la page",
            "{glossaire_recent}": "Termes récemment ajoutés au glossaire",
            "{pages_recentes}": "Contenu des pages récentes pour résumé"
        }
        
        for tag in tags:
            description = tag_descriptions.get(tag, "")
            html += f"<li><code>{tag}</code> - {description}</li>"
        
        html += "</ul>"
        self.help_panel.setHtml(html)
    
    def validate_tags(self):
        """Valide les balises utilisées dans le prompt."""
        key = self.get_current_prompt_key()
        content = self.editor.toPlainText()
        
        # Extraire toutes les balises du prompt
        used_tags = set(re.findall(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', content))
        
        # Balises disponibles pour ce type de prompt
        available_tags = set(self.AVAILABLE_TAGS.get(key, []))
        
        # Vérifier les balises invalides
        invalid_tags = used_tags - available_tags
        
        if invalid_tags:
            QMessageBox.warning(
                self,
                "Balises invalides",
                f"Les balises suivantes ne sont pas disponibles pour ce prompt:\n" +
                "\n".join(invalid_tags)
            )
        else:
            QMessageBox.information(
                self,
                "Validation",
                "Toutes les balises sont valides !"
            )
    
    def save_current_prompt(self):
        """Sauvegarde le prompt actuellement édité."""
        key = self.get_current_prompt_key()
        self.prompts[key] = self.editor.toPlainText()
        logger.debug(f"Prompt sauvegardé: {key}")
    
    def reset_current_prompt(self):
        """Réinitialise le prompt actuel aux valeurs par défaut."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment réinitialiser ce prompt ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.load_default_prompts()
            key = self.get_current_prompt_key()
            self.editor.setPlainText(self.prompts.get(key, ""))
    
    def load_default_prompts(self):
        """Charge les prompts par défaut depuis le fichier template."""
        try:
            self._loading = True  # Activer le flag de chargement
            
            template_file = Path("templates/default_prompts.json")
            
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.prompts = json.load(f)
                
                # Charger le premier prompt dans l'éditeur
                key = self.get_current_prompt_key()
                self._current_prompt_key = key
                self.editor.setPlainText(self.prompts.get(key, ""))
                
                logger.info("Prompts par défaut chargés")
            else:
                logger.warning(f"Fichier de prompts par défaut introuvable: {template_file}")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement des prompts par défaut: {e}")
        finally:
            self._loading = False  # Désactiver le flag
    
    def load_from_project(self, project: Project):
        """
        Charge les prompts depuis un projet.
        
        Args:
            project: Instance de Project
        """
        self._loading = True  # Activer le flag
        
        try:
            if project.prompts:
                self.prompts = project.prompts.copy()
                
                # Charger dans l'éditeur
                key = self.get_current_prompt_key()
                self._current_prompt_key = key
                self.editor.setPlainText(self.prompts.get(key, ""))
                
                logger.debug("Prompts chargés depuis le projet")
            else:
                # Utiliser les prompts par défaut si le projet n'en a pas
                self.load_default_prompts()
        finally:
            self._loading = False  # Désactiver le flag
    
    def save_to_project(self, project: Project):
        """
        Sauvegarde les prompts dans un projet.
        
        Args:
            project: Instance de Project
        """
        # Sauvegarder le prompt actuel avant d'exporter
        self.save_current_prompt()
        
        project.prompts = self.prompts.copy()
        logger.debug("Prompts sauvegardés dans le projet")
    
    def get_prompts(self) -> dict:
        """
        Retourne tous les prompts.
        
        Returns:
            Dict avec tous les prompts
        """
        self.save_current_prompt()
        return self.prompts.copy()
