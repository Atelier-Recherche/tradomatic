"""
Gestion du glossaire dynamique avec base SQLite.
"""

import sqlite3
import json
import csv
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class Glossary:
    """
    Gestionnaire du glossaire de traduction avec persistance SQLite.
    """
    
    def __init__(self, db_path: str):
        """
        Initialise le glossaire.
        
        Args:
            db_path: Chemin vers la base de données SQLite
        """
        self.db_path = db_path
        self._create_database()
    
    def _create_database(self):
        """Crée la base de données et les tables si nécessaire."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossaire (
                terme_de TEXT PRIMARY KEY,
                terme_fr TEXT NOT NULL,
                premiere_apparition INTEGER,
                derniere_utilisation INTEGER,
                frequence INTEGER DEFAULT 1,
                contextes TEXT,
                note TEXT,
                date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index pour recherches rapides
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_frequence 
            ON glossaire(frequence DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_premiere_apparition 
            ON glossaire(premiere_apparition)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Base de données glossaire initialisée: {self.db_path}")
    
    def add_term(self, terme_de: str, terme_fr: str, page: int, 
                 context: str = "", note: str = ""):
        """
        Ajoute un nouveau terme au glossaire.
        
        Args:
            terme_de: Terme source
            terme_fr: Traduction cible
            page: Numéro de page de première apparition
            context: Contexte d'utilisation
            note: Note explicative optionnelle
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Préparer les contextes en JSON
            contextes_list = [context] if context else []
            contextes_json = json.dumps(contextes_list, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO glossaire 
                (terme_de, terme_fr, premiere_apparition, derniere_utilisation, 
                 frequence, contextes, note)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (terme_de, terme_fr, page, page, contextes_json, note))
            
            conn.commit()
            logger.debug(f"Terme ajouté: {terme_de} → {terme_fr}")
            
        except sqlite3.IntegrityError:
            # Le terme existe déjà, on le met à jour
            logger.warning(f"Terme déjà existant: {terme_de}, mise à jour...")
            self.update_term(terme_de, terme_fr, page, context, note)
        
        finally:
            conn.close()
    
    def get_term(self, terme_de: str) -> Optional[Dict]:
        """
        Récupère un terme du glossaire.
        
        Args:
            terme_de: Terme source
            
        Returns:
            Dict avec les informations du terme, ou None si non trouvé
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT terme_de, terme_fr, premiere_apparition, derniere_utilisation,
                   frequence, contextes, note, date_ajout, date_modification
            FROM glossaire
            WHERE terme_de = ?
        """, (terme_de,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "terme_de": row[0],
                "terme_fr": row[1],
                "premiere_apparition": row[2],
                "derniere_utilisation": row[3],
                "frequence": row[4],
                "contextes": json.loads(row[5]) if row[5] else [],
                "note": row[6],
                "date_ajout": row[7],
                "date_modification": row[8]
            }
        return None
    
    def update_term(self, terme_de: str, terme_fr: str, page: int, 
                    context: str = "", note: str = ""):
        """
        Met à jour un terme existant.
        
        Args:
            terme_de: Terme source
            terme_fr: Traduction cible (peut être modifiée)
            page: Numéro de page courante
            context: Nouveau contexte à ajouter
            note: Note à ajouter/modifier
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer les contextes existants
        existing = self.get_term(terme_de)
        if existing:
            contextes = existing["contextes"]
            if context and context not in contextes:
                contextes.append(context)
                # Limiter à 5 contextes max
                contextes = contextes[-5:]
            
            contextes_json = json.dumps(contextes, ensure_ascii=False)
            
            cursor.execute("""
                UPDATE glossaire
                SET terme_fr = ?,
                    derniere_utilisation = ?,
                    contextes = ?,
                    note = ?,
                    date_modification = CURRENT_TIMESTAMP
                WHERE terme_de = ?
            """, (terme_fr, page, contextes_json, note, terme_de))
            
            conn.commit()
            logger.debug(f"Terme mis à jour: {terme_de} → {terme_fr}")
        
        conn.close()
    
    def update_frequency(self, terme_de: str, page: int = None):
        """
        Incrémente la fréquence d'utilisation d'un terme.
        
        Args:
            terme_de: Terme source
            page: Numéro de page courante (optionnel)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if page:
            cursor.execute("""
                UPDATE glossaire
                SET frequence = frequence + 1,
                    derniere_utilisation = ?,
                    date_modification = CURRENT_TIMESTAMP
                WHERE terme_de = ?
            """, (page, terme_de))
        else:
            cursor.execute("""
                UPDATE glossaire
                SET frequence = frequence + 1,
                    date_modification = CURRENT_TIMESTAMP
                WHERE terme_de = ?
            """, (terme_de,))
        
        conn.commit()
        conn.close()
    
    def get_all_terms(self) -> Dict[str, str]:
        """
        Retourne tous les termes du glossaire.
        
        Returns:
            Dict {terme_de: terme_fr}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT terme_de, terme_fr FROM glossaire")
        terms = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return terms
    
    def get_all_terms_detailed(self) -> List[Dict]:
        """
        Retourne tous les termes avec détails complets.
        
        Returns:
            Liste de dictionnaires avec toutes les informations
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT terme_de, terme_fr, premiere_apparition, derniere_utilisation,
                   frequence, contextes, note
            FROM glossaire
            ORDER BY frequence DESC
        """)
        
        terms = []
        for row in cursor.fetchall():
            terms.append({
                "terme_de": row[0],
                "terme_fr": row[1],
                "premiere_apparition": row[2],
                "derniere_utilisation": row[3],
                "frequence": row[4],
                "contextes": json.loads(row[5]) if row[5] else [],
                "note": row[6]
            })
        
        conn.close()
        return terms
    
    def get_recent_terms(self, limit: int = 200) -> Dict[str, str]:
        """
        Retourne les termes ajoutés récemment.
        
        Args:
            limit: Nombre maximum de termes à retourner
            
        Returns:
            Dict {terme_de: terme_fr}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT terme_de, terme_fr
            FROM glossaire
            ORDER BY date_ajout DESC
            LIMIT ?
        """, (limit,))
        
        terms = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return terms
    
    def consolidate(self, consolidated_data: Dict[str, str]):
        """
        Remplace les termes après consolidation.
        
        Args:
            consolidated_data: Dict {terme_de: terme_fr} avec traductions harmonisées
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for terme_de, terme_fr in consolidated_data.items():
            cursor.execute("""
                UPDATE glossaire
                SET terme_fr = ?,
                    date_modification = CURRENT_TIMESTAMP
                WHERE terme_de = ?
            """, (terme_fr, terme_de))
        
        conn.commit()
        conn.close()
        logger.info(f"Glossaire consolidé: {len(consolidated_data)} termes mis à jour")
    
    def export_json(self, filepath: str = None) -> str:
        """
        Exporte le glossaire en JSON.
        
        Args:
            filepath: Chemin du fichier (optionnel, sinon retourne la chaîne)
            
        Returns:
            Chaîne JSON
        """
        terms = self.get_all_terms_detailed()
        json_str = json.dumps(terms, ensure_ascii=False, indent=2)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"Glossaire exporté en JSON: {filepath}")
        
        return json_str
    
    def import_json(self, filepath: str):
        """
        Importe un glossaire depuis un fichier JSON.
        
        Args:
            filepath: Chemin du fichier JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            terms = json.load(f)
        
        # Vider le glossaire actuel
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM glossaire")
        conn.commit()
        
        # Importer les termes
        for term in terms:
            self.add_term(
                terme_de=term['terme_de'],
                terme_fr=term['terme_fr'],
                page=term.get('premiere_apparition', 1),
                context="",
                note=term.get('note', '')
            )
            
            # Mettre à jour la fréquence et dernière utilisation
            cursor.execute("""
                UPDATE glossaire 
                SET frequence = ?, derniere_utilisation = ?
                WHERE terme_de = ?
            """, (term.get('frequence', 1), term.get('derniere_utilisation', 1), term['terme_de']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Glossaire importé depuis JSON: {filepath} ({len(terms)} termes)")
    
    def export_csv(self, filepath: str):
        """
        Exporte le glossaire en CSV.
        
        Args:
            filepath: Chemin du fichier CSV
        """
        terms = self.get_all_terms_detailed()
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'terme_de', 'terme_fr', 'frequence', 'premiere_page', 
                'derniere_page', 'note'
            ])
            
            for term in terms:
                writer.writerow([
                    term['terme_de'],
                    term['terme_fr'],
                    term['frequence'],
                    term['premiere_apparition'],
                    term['derniere_utilisation'],
                    term['note']
                ])
        
        logger.info(f"Glossaire exporté en CSV: {filepath}")
    
    def export_markdown(self, filepath: str):
        """
        Exporte le glossaire en Markdown pour intégration dans le livre.
        
        Args:
            filepath: Chemin du fichier Markdown
        """
        terms = self.get_all_terms_detailed()
        
        # Trier par ordre alphabétique (terme source)
        terms_sorted = sorted(terms, key=lambda t: t['terme_de'].lower())
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Glossaire terminologique\n\n")
            f.write("*Glossaire des termes spécialisés utilisés dans la traduction.*\n\n")
            f.write("---\n\n")
            
            for term in terms_sorted:
                # Terme source en gras
                f.write(f"**{term['terme_de']}** : {term['terme_fr']}")
                
                # Note si présente
                if term.get('note'):
                    f.write(f"  \n*{term['note']}*")
                
                # Fréquence et pages
                f.write(f"  \n*Fréquence : {term['frequence']} | ")
                f.write(f"Pages {term['premiere_apparition']}-{term['derniere_utilisation']}*\n\n")
        
        logger.info(f"Glossaire exporté en Markdown: {filepath}")
    
    def get_size(self) -> int:
        """
        Retourne le nombre de termes dans le glossaire.
        
        Returns:
            Nombre de termes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM glossaire")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_stats(self) -> Dict:
        """
        Retourne des statistiques sur le glossaire.
        
        Returns:
            Dict avec statistiques
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM glossaire")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(frequence) FROM glossaire")
        avg_freq = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT terme_de, terme_fr, frequence FROM glossaire ORDER BY frequence DESC LIMIT 10")
        top_terms = [{"terme_de": row[0], "terme_fr": row[1], "frequence": row[2]} 
                     for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_terms": total,
            "average_frequency": round(avg_freq, 2),
            "top_terms": top_terms
        }
    
    def clear(self):
        """Vide complètement le glossaire."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM glossaire")
        conn.commit()
        conn.close()
        
        logger.warning("Glossaire vidé complètement")
