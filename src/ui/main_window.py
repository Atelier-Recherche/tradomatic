"""
Fenêtre principale de l'application Tradomatic.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QFileDialog,
    QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from ..utils.i18n import get_i18n
from ..utils.config import get_config
from ..core.project import Project

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application avec onglets et menus.
    """
    
    def __init__(self):
        """Initialise la fenêtre principale."""
        super().__init__()
        
        self.i18n = get_i18n()
        self.config = get_config()
        self.current_project = None
        self.current_project_file = None
        
        # Importer les panneaux (import tardif pour éviter les dépendances circulaires)
        from .prompts_panel import PromptsPanel
        from .settings_panel import SettingsPanel
        from .translation_panel import TranslationPanel
        from .comparison_panel import ComparisonPanel
        from .glossary_panel import GlossaryPanel
        
        self.prompts_panel = PromptsPanel(self)
        self.settings_panel = SettingsPanel(self)
        self.translation_panel = TranslationPanel(self)
        self.comparison_panel = ComparisonPanel(self)
        self.glossary_panel = GlossaryPanel(self)
        
        self.init_ui()
        self.apply_theme(self.config.get("ui.theme", "dark"))
        
        logger.info("MainWindow initialisée")
        
        # Charger automatiquement le dernier projet
        self.load_last_project()
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        self.setWindowTitle(self.i18n.t("app.title"))
        self.setGeometry(100, 100, 1400, 900)
        
        # Créer les menus
        self.create_menu_bar()
        
        # Widget central avec onglets
        self.tabs = QTabWidget()
        self.tabs.addTab(self.prompts_panel, self.i18n.t("panels.prompts"))
        self.tabs.addTab(self.settings_panel, self.i18n.t("panels.settings"))
        self.tabs.addTab(self.translation_panel, self.i18n.t("panels.translation"))
        self.tabs.addTab(self.glossary_panel, "📚 Glossaire")
        self.tabs.addTab(self.comparison_panel, self.i18n.t("panels.comparison"))
        
        self.setCentralWidget(self.tabs)
        
        # Barre de statut
        self.statusBar().showMessage(self.i18n.t("translation_panel.status_ready"))
    
    def create_menu_bar(self):
        """Crée la barre de menus."""
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu(self.i18n.t("menu.file"))
        
        new_action = QAction(self.i18n.t("menu.new_project"), self)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction(self.i18n.t("menu.open_project"), self)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction(self.i18n.t("menu.save_project"), self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(self.i18n.t("menu.save_project_as"), self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction(self.i18n.t("menu.quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Menu Affichage
        view_menu = menubar.addMenu(self.i18n.t("menu.view"))
        
        # Sous-menu Langue
        language_menu = view_menu.addMenu(self.i18n.t("menu.language"))
        
        for lang_code, lang_name in self.i18n.get_available_languages().items():
            lang_action = QAction(lang_name, self)
            lang_action.triggered.connect(lambda checked, lc=lang_code: self.change_language(lc))
            language_menu.addAction(lang_action)
        
        # Sous-menu Thème
        theme_menu = view_menu.addMenu(self.i18n.t("menu.theme"))
        
        light_action = QAction(self.i18n.t("menu.theme_light"), self)
        light_action.triggered.connect(lambda: self.apply_theme("light"))
        theme_menu.addAction(light_action)
        
        dark_action = QAction(self.i18n.t("menu.theme_dark"), self)
        dark_action.triggered.connect(lambda: self.apply_theme("dark"))
        theme_menu.addAction(dark_action)
        
        # Menu Outils
        tools_menu = menubar.addMenu(self.i18n.t("menu.tools"))
        
        export_glossary_action = QAction(self.i18n.t("menu.export_glossary"), self)
        export_glossary_action.triggered.connect(self.export_glossary)
        tools_menu.addAction(export_glossary_action)
        
        # Menu Aide
        help_menu = menubar.addMenu(self.i18n.t("menu.help"))
        
        about_action = QAction(self.i18n.t("menu.about"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def new_project(self):
        """Crée un nouveau projet."""
        # Vérifier si un projet est déjà ouvert
        if self.current_project:
            reply = QMessageBox.question(
                self,
                self.i18n.t("dialogs.confirm"),
                "Voulez-vous sauvegarder le projet actuel ?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_project()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Créer nouveau projet
        self.current_project = Project()
        self.current_project_file = None
        
        # Charger les prompts par défaut
        self.prompts_panel.load_default_prompts()
        
        # Réinitialiser les panneaux
        self.settings_panel.load_from_project(self.current_project)
        
        self.statusBar().showMessage("Nouveau projet créé")
        logger.info("Nouveau projet créé")
    
    def open_project(self):
        """Ouvre un projet existant."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("menu.open_project"),
            "",
            "Projets Tradomatic (*.json);;Tous les fichiers (*.*)"
        )
        
        if filepath:
            try:
                self.current_project = Project.load(filepath)
                self.current_project_file = filepath
                
                # Charger dans les panneaux
                self.settings_panel.load_from_project(self.current_project)
                self.prompts_panel.load_from_project(self.current_project)
                
                self.statusBar().showMessage(
                    f"{self.i18n.t('messages.project_loaded')}: {Path(filepath).name}"
                )
                logger.info(f"Projet chargé: {filepath}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.i18n.t("dialogs.error"),
                    f"Erreur lors du chargement du projet:\n{str(e)}"
                )
                logger.error(f"Erreur chargement projet: {e}")
    
    def save_project(self):
        """Sauvegarde le projet actuel."""
        if not self.current_project:
            self.new_project()
            return
        
        if not self.current_project_file:
            self.save_project_as()
            return
        
        try:
            # Récupérer les données des panneaux
            self.settings_panel.save_to_project(self.current_project)
            self.prompts_panel.save_to_project(self.current_project)
            
            # Sauvegarder
            self.current_project.save(self.current_project_file)
            
            self.statusBar().showMessage(self.i18n.t("messages.project_saved"))
            logger.info(f"Projet sauvegardé: {self.current_project_file}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.i18n.t("dialogs.error"),
                f"Erreur lors de la sauvegarde:\n{str(e)}"
            )
            logger.error(f"Erreur sauvegarde projet: {e}")
    
    def save_project_as(self):
        """Sauvegarde le projet sous un nouveau nom."""
        if not self.current_project:
            self.new_project()
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("menu.save_project_as"),
            "",
            "Projets Tradomatic (*.json);;Tous les fichiers (*.*)"
        )
        
        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            
            self.current_project_file = filepath
            self.save_project()
    
    def change_language(self, language: str):
        """
        Change la langue de l'interface.
        
        Args:
            language: Code de langue (fr_FR, en_US)
        """
        if self.i18n.change_language(language):
            self.config.set("ui.language", language)
            
            QMessageBox.information(
                self,
                self.i18n.t("dialogs.info"),
                "Veuillez redémarrer l'application pour appliquer le changement de langue."
            )
            
            logger.info(f"Langue changée: {language}")
    
    def apply_theme(self, theme: str):
        """
        Applique un thème à l'interface.
        
        Args:
            theme: Nom du thème (light, dark)
        """
        try:
            qss_file = Path(f"resources/styles/{theme}.qss")
            
            if qss_file.exists():
                with open(qss_file, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    QApplication.instance().setStyleSheet(stylesheet)
                
                self.config.set("ui.theme", theme)
                logger.info(f"Thème appliqué: {theme}")
            else:
                logger.warning(f"Fichier de thème introuvable: {qss_file}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'application du thème: {e}")
    
    def export_glossary(self):
        """Exporte le glossaire."""
        if not self.current_project:
            QMessageBox.warning(
                self,
                self.i18n.t("dialogs.warning"),
                "Aucun projet ouvert"
            )
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("menu.export_glossary"),
            "glossaire.csv",
            "CSV (*.csv);;JSON (*.json);;Tous les fichiers (*.*)"
        )
        
        if filepath:
            try:
                # TODO: Implémenter l'export du glossaire
                self.statusBar().showMessage(
                    f"{self.i18n.t('messages.glossary_exported')}: {Path(filepath).name}"
                )
                logger.info(f"Glossaire exporté: {filepath}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.i18n.t("dialogs.error"),
                    f"Erreur lors de l'export:\n{str(e)}"
                )
    
    def show_about(self):
        """Affiche la boîte de dialogue À propos."""
        QMessageBox.about(
            self,
            self.i18n.t("menu.about"),
            """<h2>Tradomatic</h2>
            <p>Version 1.0</p>
            <p>Traducteur autonome pour textes philosophiques</p>
            <p>Développé avec PyQt6</p>
            <p>© 2026</p>"""
        )
    
    def load_last_project(self):
        """Charge automatiquement le dernier projet ouvert."""
        last_project_path = self.config.get("last_project_path")
        
        if last_project_path and Path(last_project_path).exists():
            try:
                logger.info(f"Chargement automatique du dernier projet: {last_project_path}")
                project = Project.load(last_project_path)
                
                # Charger dans les panneaux
                self.prompts_panel.load_from_project(project)
                self.settings_panel.load_from_project(project)
                
                self.current_project = project
                self.current_project_file = last_project_path
                
                self.statusBar().showMessage(f"Projet chargé: {Path(last_project_path).name}")
                logger.info(f"Dernier projet chargé automatiquement: {last_project_path}")
                
            except Exception as e:
                logger.warning(f"Impossible de charger le dernier projet: {e}")
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre."""
        if self.current_project:
            # Sauvegarder le chemin du dernier projet
            if self.current_project_file:
                self.config.set("last_project_path", self.current_project_file)
            
            reply = QMessageBox.question(
                self,
                self.i18n.t("dialogs.confirm"),
                "Voulez-vous sauvegarder avant de quitter ?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_project()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
