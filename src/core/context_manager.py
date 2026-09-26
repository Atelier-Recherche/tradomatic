"""
Gestionnaire de contexte glissant pour maintenir la cohérence narrative.
"""

import logging
from typing import List, Dict
from collections import deque

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Gère une fenêtre glissante de résumés pour maintenir le contexte narratif.
    """
    
    def __init__(self, window_size: int = 5, pages_per_summary: int = 10):
        """
        Initialise le gestionnaire de contexte.
        
        Args:
            window_size: Nombre de résumés à conserver (fenêtre glissante)
            pages_per_summary: Nombre de pages avant de générer un résumé
        """
        self.window_size = window_size
        self.pages_per_summary = pages_per_summary
        
        # FIFO de résumés (deque pour rotation efficace)
        self.summaries = deque(maxlen=window_size)
        
        # Buffer des pages récentes (pour génération de résumé)
        self.pages_buffer = []
        
        # Compteur de pages
        self.page_count = 0
        
        logger.info(f"ContextManager initialisé: fenêtre={window_size}, "
                   f"pages/résumé={pages_per_summary}")
    
    def add_page(self, page_num: int, content: str):
        """
        Ajoute une page au buffer.
        
        Args:
            page_num: Numéro de la page
            content: Contenu traduit de la page
        """
        self.pages_buffer.append({
            "page_num": page_num,
            "content": content
        })
        self.page_count += 1
        
        logger.debug(f"Page {page_num} ajoutée au buffer "
                    f"({len(self.pages_buffer)}/{self.pages_per_summary})")
    
    def should_generate_summary(self) -> bool:
        """
        Vérifie si un résumé doit être généré.
        
        Returns:
            bool: True si le buffer contient assez de pages
        """
        return len(self.pages_buffer) >= self.pages_per_summary
    
    def get_pages_for_summary(self) -> List[str]:
        """
        Retourne les pages du buffer pour génération de résumé.
        
        Returns:
            Liste des contenus de pages
        """
        return [page["content"] for page in self.pages_buffer]
    
    def add_summary(self, summary: str):
        """
        Ajoute un résumé à la fenêtre glissante et vide le buffer.
        
        Args:
            summary: Texte du résumé généré
        """
        # Ajouter le résumé (deque gère automatiquement la rotation)
        self.summaries.append({
            "pages_range": (
                self.pages_buffer[0]["page_num"],
                self.pages_buffer[-1]["page_num"]
            ),
            "summary": summary
        })
        
        logger.info(f"Résumé ajouté pour pages "
                   f"{self.pages_buffer[0]['page_num']}-{self.pages_buffer[-1]['page_num']} "
                   f"(total résumés: {len(self.summaries)})")
        
        # Vider le buffer
        self.pages_buffer = []
    
    def get_context(self) -> str:
        """
        Retourne le contexte complet (tous les résumés de la fenêtre).
        
        Returns:
            str: Contexte narratif formaté
        """
        if not self.summaries:
            return "Aucun contexte disponible (début de la traduction)."
        
        context_parts = []
        for summary_data in self.summaries:
            pages_range = summary_data["pages_range"]
            summary = summary_data["summary"]
            context_parts.append(
                f"Pages {pages_range[0]}-{pages_range[1]} :\n{summary}"
            )
        
        return "\n\n".join(context_parts)
    
    def get_summary_count(self) -> int:
        """
        Retourne le nombre de résumés actuellement stockés.
        
        Returns:
            int: Nombre de résumés
        """
        return len(self.summaries)
    
    def get_pages_count(self) -> int:
        """
        Retourne le nombre total de pages traitées.
        
        Returns:
            int: Nombre de pages
        """
        return self.page_count
    
    def export_state(self) -> Dict:
        """
        Exporte l'état complet du gestionnaire (pour checkpoint).
        
        Returns:
            Dict avec l'état complet
        """
        return {
            "window_size": self.window_size,
            "pages_per_summary": self.pages_per_summary,
            "summaries": list(self.summaries),
            "pages_buffer": self.pages_buffer,
            "page_count": self.page_count
        }
    
    def import_state(self, state: Dict):
        """
        Importe un état sauvegardé (pour reprise après checkpoint).
        
        Args:
            state: Dict avec l'état à restaurer
        """
        self.window_size = state["window_size"]
        self.pages_per_summary = state["pages_per_summary"]
        self.summaries = deque(state["summaries"], maxlen=self.window_size)
        self.pages_buffer = state["pages_buffer"]
        self.page_count = state["page_count"]
        
        logger.info(f"État du contexte restauré: {self.page_count} pages, "
                   f"{len(self.summaries)} résumés")
    
    def clear(self):
        """Réinitialise complètement le gestionnaire de contexte."""
        self.summaries.clear()
        self.pages_buffer = []
        self.page_count = 0
        logger.info("Contexte réinitialisé")
    
    def get_stats(self) -> Dict:
        """
        Retourne des statistiques sur le contexte.
        
        Returns:
            Dict avec statistiques
        """
        return {
            "total_pages": self.page_count,
            "summaries_count": len(self.summaries),
            "pages_in_buffer": len(self.pages_buffer),
            "window_size": self.window_size,
            "pages_per_summary": self.pages_per_summary
        }
