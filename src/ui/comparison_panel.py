"""
Panneau de comparaison côte à côte source/traduction.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QSpinBox, QPushButton, QSplitter, QCheckBox, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt

from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


class ComparisonPanel(QWidget):
    """
    Panneau de comparaison avec vue côte à côte.
    """
    
    def __init__(self, parent=None):
        """Initialise le panneau."""
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self.parent_window = parent
        
        # Stockage des pages
        self.pages = {}  # {page_num: {"source": str, "translation": str}}
        self.current_page = 1
        
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout()
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        page_label = QLabel(self.i18n.t("comparison_panel.page"))
        nav_layout.addWidget(page_label)
        
        self.page_selector = QSpinBox()
        self.page_selector.setMinimum(1)
        self.page_selector.setMaximum(1)
        self.page_selector.setValue(1)
        self.page_selector.valueChanged.connect(self.on_page_changed)
        nav_layout.addWidget(self.page_selector)
        
        self.prev_btn = QPushButton(self.i18n.t("buttons.previous"))
        self.prev_btn.clicked.connect(self.previous_page)
        nav_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton(self.i18n.t("buttons.next"))
        self.next_btn.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_btn)
        
        nav_layout.addStretch()
        
        self.load_pages_btn = QPushButton("📂 Charger pages traduites")
        self.load_pages_btn.clicked.connect(self.load_existing_pages)
        nav_layout.addWidget(self.load_pages_btn)
        
        self.sync_scroll_cb = QCheckBox(self.i18n.t("comparison_panel.sync_scroll"))
        self.sync_scroll_cb.setChecked(True)
        nav_layout.addWidget(self.sync_scroll_cb)
        
        self.export_html_btn = QPushButton(self.i18n.t("comparison_panel.export_html"))
        self.export_html_btn.clicked.connect(self.export_to_html)
        nav_layout.addWidget(self.export_html_btn)
        
        layout.addLayout(nav_layout)
        
        # Splitter avec deux panneaux
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panneau gauche : source
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_label = QLabel(self.i18n.t("comparison_panel.source"))
        left_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        left_layout.addWidget(left_label)
        
        self.source_viewer = QTextBrowser()
        self.source_viewer.setReadOnly(True)
        self.source_viewer.verticalScrollBar().valueChanged.connect(
            self.on_source_scroll
        )
        left_layout.addWidget(self.source_viewer)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Panneau droit : traduction
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_label = QLabel(self.i18n.t("comparison_panel.translation"))
        right_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        right_layout.addWidget(right_label)
        
        self.translation_viewer = QTextBrowser()
        self.translation_viewer.setReadOnly(True)
        self.translation_viewer.verticalScrollBar().valueChanged.connect(
            self.on_translation_scroll
        )
        right_layout.addWidget(self.translation_viewer)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Taille égale pour les deux panneaux
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
        # Variables pour synchronisation du scroll
        self._sync_in_progress = False
    
    def load_existing_pages(self):
        """Charge toutes les pages déjà traduites depuis le projet."""
        if not self.parent_window.current_project:
            return
        
        project = self.parent_window.current_project
        input_dir = Path(project.paths.get("input_directory", ""))
        output_dir = Path(project.paths.get("output_directory", ""))
        
        if not input_dir.exists() or not output_dir.exists():
            return
        
        # Récupérer tous les fichiers d'entrée
        input_files = sorted(input_dir.glob("*.md"))
        
        # Charger les pages traduites
        pages_loaded = 0
        for i, input_file in enumerate(input_files, start=1):
            output_file = output_dir / f"page_{i:04d}.md"
            
            if output_file.exists():
                try:
                    # Lire source
                    with open(input_file, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    # Lire traduction
                    with open(output_file, 'r', encoding='utf-8') as f:
                        translation = f.read()
                    
                    self.add_page(i, source, translation)
                    pages_loaded += 1
                except Exception as e:
                    logger.warning(f"Erreur lors du chargement de la page {i}: {e}")
        
        if pages_loaded > 0:
            logger.info(f"{pages_loaded} page(s) chargée(s) dans la comparaison")
            self.display_page(1)
    
    def add_page(self, page_num: int, source: str, translation: str):
        """
        Ajoute une page à la comparaison.
        
        Args:
            page_num: Numéro de page
            source: Texte source
            translation: Traduction
        """
        self.pages[page_num] = {
            "source": source,
            "translation": translation
        }
        
        # Mettre à jour le maximum du sélecteur
        if self.pages:
            max_page = max(self.pages.keys())
            self.page_selector.setMaximum(max_page)
        
        # Afficher automatiquement la page ajoutée
        self.current_page = page_num
        self.display_page(page_num)
        
        logger.debug(f"Page {page_num} ajoutée à la comparaison")
    
    def display_page(self, page_num: int):
        """
        Affiche une page dans les viewers.
        
        Args:
            page_num: Numéro de page
        """
        if page_num not in self.pages:
            self.source_viewer.setPlainText("Page non disponible")
            self.translation_viewer.setPlainText("Page non disponible")
            return
        
        page_data = self.pages[page_num]
        
        # Afficher le texte source
        self.source_viewer.setPlainText(page_data["source"])
        
        # Afficher la traduction
        self.translation_viewer.setPlainText(page_data["translation"])
        
        self.current_page = page_num
        logger.debug(f"Page {page_num} affichée")
    
    def on_page_changed(self, page_num: int):
        """
        Appelé quand le numéro de page change.
        
        Args:
            page_num: Nouveau numéro de page
        """
        self.display_page(page_num)
    
    def previous_page(self):
        """Affiche la page précédente."""
        if self.current_page > 1:
            self.page_selector.setValue(self.current_page - 1)
    
    def next_page(self):
        """Affiche la page suivante."""
        max_page = self.page_selector.maximum()
        if self.current_page < max_page:
            self.page_selector.setValue(self.current_page + 1)
    
    def on_source_scroll(self, value):
        """
        Synchronise le scroll du panneau de traduction avec la source.
        
        Args:
            value: Valeur du scrollbar
        """
        if not self.sync_scroll_cb.isChecked() or self._sync_in_progress:
            return
        
        self._sync_in_progress = True
        
        # Calculer le pourcentage de scroll
        source_scrollbar = self.source_viewer.verticalScrollBar()
        max_val = source_scrollbar.maximum()
        
        if max_val > 0:
            percentage = value / max_val
            
            # Appliquer au panneau de traduction
            translation_scrollbar = self.translation_viewer.verticalScrollBar()
            translation_max = translation_scrollbar.maximum()
            new_value = int(percentage * translation_max)
            translation_scrollbar.setValue(new_value)
        
        self._sync_in_progress = False
    
    def on_translation_scroll(self, value):
        """
        Synchronise le scroll du panneau source avec la traduction.
        
        Args:
            value: Valeur du scrollbar
        """
        if not self.sync_scroll_cb.isChecked() or self._sync_in_progress:
            return
        
        self._sync_in_progress = True
        
        # Calculer le pourcentage de scroll
        translation_scrollbar = self.translation_viewer.verticalScrollBar()
        max_val = translation_scrollbar.maximum()
        
        if max_val > 0:
            percentage = value / max_val
            
            # Appliquer au panneau source
            source_scrollbar = self.source_viewer.verticalScrollBar()
            source_max = source_scrollbar.maximum()
            new_value = int(percentage * source_max)
            source_scrollbar.setValue(new_value)
        
        self._sync_in_progress = False
    
    def export_to_html(self):
        """Exporte la comparaison en HTML."""
        if not self.pages:
            QMessageBox.warning(
                self,
                self.i18n.t("dialogs.warning"),
                "Aucune page à exporter"
            )
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("comparison_panel.export_html"),
            "comparaison.html",
            "HTML (*.html);;Tous les fichiers (*.*)"
        )
        
        if filepath:
            try:
                self._generate_html_export(filepath)
                
                QMessageBox.information(
                    self,
                    self.i18n.t("dialogs.success"),
                    f"Comparaison exportée: {Path(filepath).name}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.i18n.t("dialogs.error"),
                    f"Erreur lors de l'export:\n{str(e)}"
                )
                logger.error(f"Erreur export HTML: {e}")
    
    def _generate_html_export(self, filepath: str):
        """
        Génère le fichier HTML d'export.
        
        Args:
            filepath: Chemin du fichier de sortie
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Comparaison Traduction</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .page {
            background-color: white;
            margin-bottom: 30px;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .page-header {
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 20px;
            color: #0078d4;
        }
        .comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .column {
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .column-header {
            font-weight: bold;
            margin-bottom: 10px;
            color: #666;
        }
        .source {
            background-color: #fff8dc;
        }
        .translation {
            background-color: #e6f3ff;
        }
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
    </style>
</head>
<body>
    <h1>Comparaison Source / Traduction</h1>
"""
        
        # Ajouter chaque page
        for page_num in sorted(self.pages.keys()):
            page_data = self.pages[page_num]
            
            html += f"""
    <div class="page">
        <div class="page-header">Page {page_num}</div>
        <div class="comparison">
            <div class="column source">
                <div class="column-header">Source (DE)</div>
                <pre>{self._escape_html(page_data['source'])}</pre>
            </div>
            <div class="column translation">
                <div class="column-header">Traduction (FR)</div>
                <pre>{self._escape_html(page_data['translation'])}</pre>
            </div>
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Comparaison exportée en HTML: {filepath}")
    
    def _escape_html(self, text: str) -> str:
        """
        Échappe les caractères HTML.
        
        Args:
            text: Texte à échapper
            
        Returns:
            Texte échappé
        """
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def clear(self):
        """Vide toutes les pages."""
        self.pages = {}
        self.current_page = 1
        self.page_selector.setMaximum(1)
        self.page_selector.setValue(1)
        self.source_viewer.clear()
        self.translation_viewer.clear()
        logger.info("Panneau de comparaison vidé")
