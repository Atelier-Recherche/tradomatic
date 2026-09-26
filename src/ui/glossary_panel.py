"""
Panneau d'affichage du glossaire en temps réel.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QHeaderView, QGroupBox, QFileDialog,
    QMessageBox, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from pathlib import Path

from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


class GlossaryPanel(QWidget):
    """
    Panneau d'affichage et de recherche dans le glossaire.
    """
    
    def __init__(self, parent=None):
        """Initialise le panneau."""
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self.parent_window = parent
        self.glossary = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialise l'interface."""
        layout = QVBoxLayout()
        
        # Statistiques
        stats_group = QGroupBox("Statistiques du glossaire")
        stats_layout = QHBoxLayout()
        
        self.total_label = QLabel("Total : 0 termes")
        stats_layout.addWidget(self.total_label)
        
        self.avg_freq_label = QLabel("Fréquence moyenne : 0")
        stats_layout.addWidget(self.avg_freq_label)
        
        stats_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.clicked.connect(self.refresh_glossary)
        stats_layout.addWidget(self.refresh_btn)
        
        self.export_json_btn = QPushButton("💾 Export JSON")
        self.export_json_btn.clicked.connect(self.export_json)
        stats_layout.addWidget(self.export_json_btn)
        
        self.import_json_btn = QPushButton("📂 Import JSON")
        self.import_json_btn.clicked.connect(self.import_json)
        stats_layout.addWidget(self.import_json_btn)
        
        self.export_md_btn = QPushButton("📖 Export Markdown")
        self.export_md_btn.clicked.connect(self.export_markdown)
        stats_layout.addWidget(self.export_md_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Recherche
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Rechercher :")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Terme source ou cible...")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Table du glossaire
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Terme source", "Terme cible", "Fréquence",
            "1ère page", "Dernière page", "Note"
        ])
        
        # Ajuster les colonnes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        # Tri activé
        self.table.setSortingEnabled(True)
        
        # Menu contextuel (clic droit)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def set_glossary(self, glossary):
        """
        Définit le glossaire à afficher.
        
        Args:
            glossary: Instance de Glossary
        """
        self.glossary = glossary
        self.refresh_glossary()
    
    def refresh_glossary(self):
        """Actualise l'affichage du glossaire."""
        if not self.glossary:
            return
        
        try:
            # Récupérer les termes
            terms = self.glossary.get_all_terms_detailed()
            
            # Mettre à jour les statistiques
            stats = self.glossary.get_stats()
            self.total_label.setText(f"Total : {stats['total_terms']} termes")
            self.avg_freq_label.setText(f"Fréquence moyenne : {stats['average_frequency']}")
            
            # Remplir la table
            self.table.setRowCount(len(terms))
            self.table.setSortingEnabled(False)  # Désactiver pendant le remplissage
            
            for row, term in enumerate(terms):
                # Terme DE
                item_de = QTableWidgetItem(term['terme_de'])
                self.table.setItem(row, 0, item_de)
                
                # Terme FR
                item_fr = QTableWidgetItem(term['terme_fr'])
                self.table.setItem(row, 1, item_fr)
                
                # Fréquence
                item_freq = QTableWidgetItem(str(term['frequence']))
                item_freq.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, item_freq)
                
                # Première page
                item_first = QTableWidgetItem(str(term['premiere_apparition']))
                item_first.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, item_first)
                
                # Dernière page
                item_last = QTableWidgetItem(str(term['derniere_utilisation']))
                item_last.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, item_last)
                
                # Note
                item_note = QTableWidgetItem(term.get('note', ''))
                self.table.setItem(row, 5, item_note)
            
            self.table.setSortingEnabled(True)  # Réactiver le tri
            
            logger.debug(f"Glossaire actualisé: {len(terms)} termes")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'actualisation du glossaire: {e}")
    
    def filter_table(self, search_text: str):
        """
        Filtre la table selon le texte de recherche.
        
        Args:
            search_text: Texte à rechercher
        """
        search_lower = search_text.lower()
        
        for row in range(self.table.rowCount()):
            # Vérifier si le terme DE ou FR contient le texte
            term_de = self.table.item(row, 0).text().lower()
            term_fr = self.table.item(row, 1).text().lower()
            
            if search_lower in term_de or search_lower in term_fr:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
    def add_term_realtime(self, terme_de: str, terme_fr: str, page: int, freq: int = 1):
        """
        Ajoute un terme en temps réel pendant la traduction.
        
        Args:
            terme_de: Terme source
            terme_fr: Terme cible
            page: Numéro de page
            freq: Fréquence
        """
        # Vérifier si le terme existe déjà
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == terme_de:
                # Mettre à jour la fréquence
                freq_item = self.table.item(row, 2)
                current_freq = int(freq_item.text())
                freq_item.setText(str(current_freq + 1))
                
                # Mettre à jour la dernière page
                self.table.item(row, 4).setText(str(page))
                return
        
        # Ajouter nouveau terme
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(terme_de))
        self.table.setItem(row, 1, QTableWidgetItem(terme_fr))
        
        freq_item = QTableWidgetItem(str(freq))
        freq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, freq_item)
        
        first_item = QTableWidgetItem(str(page))
        first_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 3, first_item)
        
        last_item = QTableWidgetItem(str(page))
        last_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 4, last_item)
        
        self.table.setItem(row, 5, QTableWidgetItem(""))
        
        # Mettre à jour les stats
        if self.glossary:
            stats = self.glossary.get_stats()
            self.total_label.setText(f"Total : {stats['total_terms']} termes")
            self.avg_freq_label.setText(f"Fréquence moyenne : {stats['average_frequency']}")
    
    def export_json(self):
        """Exporte le glossaire en JSON."""
        if not self.glossary:
            QMessageBox.warning(self, "Attention", "Aucun glossaire chargé")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le glossaire en JSON",
            "glossaire.json",
            "Fichiers JSON (*.json)"
        )
        
        if filepath:
            try:
                self.glossary.export_json(filepath)
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Glossaire exporté en JSON:\n{Path(filepath).name}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Erreur lors de l'export:\n{str(e)}"
                )
    
    def import_json(self):
        """Importe un glossaire depuis JSON."""
        if not self.glossary:
            QMessageBox.warning(self, "Attention", "Aucun glossaire chargé")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "L'import va remplacer le glossaire actuel. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer un glossaire JSON",
            "",
            "Fichiers JSON (*.json)"
        )
        
        if filepath:
            try:
                self.glossary.import_json(filepath)
                self.refresh_glossary()
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Glossaire importé depuis:\n{Path(filepath).name}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Erreur lors de l'import:\n{str(e)}"
                )
    
    def export_markdown(self):
        """Exporte le glossaire en Markdown."""
        if not self.glossary:
            QMessageBox.warning(self, "Attention", "Aucun glossaire chargé")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le glossaire en Markdown",
            "glossaire.md",
            "Fichiers Markdown (*.md)"
        )
        
        if filepath:
            try:
                self.glossary.export_markdown(filepath)
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Glossaire exporté en Markdown:\n{Path(filepath).name}\n\nVous pouvez l'intégrer dans votre livre !"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Erreur lors de l'export:\n{str(e)}"
                )
    
    def show_context_menu(self, position):
        """Affiche le menu contextuel (clic droit)."""
        if not self.glossary:
            return
        
        # Récupérer l'élément cliqué
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        terme_de = self.table.item(row, 0).text()
        
        # Créer le menu
        menu = QMenu(self)
        
        delete_action = QAction("🗑️ Supprimer ce terme", self)
        delete_action.triggered.connect(lambda: self.delete_term(terme_de, row))
        menu.addAction(delete_action)
        
        # Afficher le menu
        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def delete_term(self, terme_de: str, row: int):
        """Supprime un terme du glossaire."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer le terme '{terme_de}' du glossaire ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Supprimer de la base de données
                import sqlite3
                conn = sqlite3.connect(self.glossary.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM glossaire WHERE terme_de = ?", (terme_de,))
                conn.commit()
                conn.close()
                
                # Supprimer de la table
                self.table.removeRow(row)
                
                # Mettre à jour les stats
                stats = self.glossary.get_stats()
                self.total_label.setText(f"Total : {stats['total_terms']} termes")
                self.avg_freq_label.setText(f"Fréquence moyenne : {stats['average_frequency']}")
                
                logger.info(f"Terme supprimé du glossaire: {terme_de}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Erreur lors de la suppression:\n{str(e)}"
                )
    
    def clear(self):
        """Vide la table."""
        self.table.setRowCount(0)
        self.total_label.setText("Total : 0 termes")
        self.avg_freq_label.setText("Fréquence moyenne : 0")
