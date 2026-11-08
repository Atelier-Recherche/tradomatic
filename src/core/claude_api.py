"""
Implémentation du connecteur pour l'API Claude (Anthropic).
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import anthropic

from .api_connector import APIConnector, retry

logger = logging.getLogger(__name__)


def list_claude_models(api_key: str) -> List[Tuple[str, str]]:
    """
    Liste les modèles disponibles via l'API Claude.
    
    Args:
        api_key: Clé API Anthropic
        
    Returns:
        Liste de (model_id, display_name)
    """
    client = anthropic.Anthropic(api_key=api_key)
    models = []
    
    try:
        for model in client.models.list(limit=50):
            model_id = getattr(model, 'id', None) or ''
            display = getattr(model, 'display_name', None) or model_id
            if model_id:
                models.append((model_id, f"{display} ({model_id})"))
        return models
        
    except Exception as e:
        logger.error(f"Erreur listage modèles Claude: {e}")
        raise


class ClaudeAPI(APIConnector):
    """
    Connecteur pour l'API Claude d'Anthropic.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", 
                 rate_limit: int = 60, timeout: int = 120, max_tokens: int = 4000):
        """
        Initialise le connecteur Claude.
        
        Args:
            api_key: Clé API Anthropic
            model: Modèle Claude à utiliser
            rate_limit: Limite de requêtes par minute
            timeout: Timeout en secondes
            max_tokens: Nombre maximum de tokens en sortie
        """
        super().__init__(api_key, rate_limit, timeout)
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=api_key)
        
    @retry(max_attempts=3)
    def translate_page(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Traduit une page via l'API Claude.
        """
        self._rate_limit_wait()
        
        try:
            logger.info(f"Appel API Claude (modèle: {self.model})")
            
            # LOG COMPLET : Prompt envoyé
            logger.info("=" * 80)
            logger.info("PROMPT SYSTÈME ENVOYÉ:")
            logger.info(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
            logger.info("-" * 80)
            logger.info("PROMPT UTILISATEUR ENVOYÉ:")
            logger.info(user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt)
            logger.info("=" * 80)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3  # Cohérence terminologique
            )
            
            # Extraire le contenu de la réponse
            content = response.content[0].text
            
            # LOG COMPLET : Réponse brute
            logger.info("=" * 80)
            logger.info("RÉPONSE BRUTE REÇUE:")
            logger.info(content)
            logger.info("=" * 80)
            
            # Parser le JSON
            try:
                result = json.loads(content)
                logger.debug("Réponse JSON parsée avec succès")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de parsing JSON: {e}")
                logger.debug(f"Contenu reçu: {content[:500]}...")
                
                # Tenter d'extraire le JSON s'il est enrobé de markdown
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    result = json.loads(content)
                    return result
                else:
                    raise
                    
        except anthropic.APIError as e:
            logger.error(f"Erreur API Claude: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            raise
    
    @retry(max_attempts=3)
    def consolidate_glossary(self, glossary: Dict[str, str],
                             prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Consolide le glossaire via Claude.
        """
        self._rate_limit_wait()
        
        if prompt:
            system_prompt = (
                "Tu es un expert en traduction terminologique. "
                "Analyse le glossaire fourni et détecte les incohérences."
            )
            user_prompt = prompt
        else:
            glossary_text = "\n".join([f"- {src}: {tgt}" for src, tgt in glossary.items()])
            system_prompt = (
                "Tu es un expert en traduction terminologique. "
                "Analyse le glossaire fourni et détecte les incohérences."
            )
            user_prompt = f"""Voici le glossaire actuel :

{glossary_text}

Détecte les incohérences (même concept source traduit différemment).
Propose une harmonisation raisonnée.

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown) :
{{
  "incohérences_détectées": [
    {{
      "terme_source": "...",
      "traductions_divergentes": ["traduction1", "traduction2"],
      "traduction_recommandée": "...",
      "justification": "..."
    }}
  ],
  "glossaire_consolidé": {{"terme_source": "terme_cible", ...}}
}}"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.2
            )
            
            content = response.content[0].text
            result = json.loads(content)
            return result
            
        except Exception as e:
            logger.error(f"Erreur consolidation glossaire: {e}")
            raise
    
    @retry(max_attempts=3)
    def generate_summary(self, pages: List[str],
                         prompt: Optional[str] = None) -> str:
        """
        Génère un résumé via Claude.
        """
        self._rate_limit_wait()
        
        if prompt:
            user_prompt = prompt
        else:
            pages_text = "\n\n---\n\n".join(pages)
            user_prompt = f"""Résume en 200 mots le contenu et l'argumentation de ces pages :

{pages_text}

Focus sur : concepts développés, thèses avancées, transitions argumentatives."""
        
        system_prompt = (
            "Tu es un expert en synthèse de textes. "
            "Résume de manière concise le contenu fourni."
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erreur génération résumé: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Claude.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                messages=[{"role": "user", "content": "Test"}]
            )
            logger.info("Test de connexion Claude réussi")
            return True
        except Exception as e:
            logger.error(f"Test de connexion Claude échoué: {e}")
            return False
