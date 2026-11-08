"""
Implémentation du connecteur pour l'API Gemini (Google).
Supporte Gemini et Gemma.
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import google.generativeai as genai

from .api_connector import APIConnector, retry

logger = logging.getLogger(__name__)


def list_gemini_models(api_key: str) -> List[Tuple[str, str]]:
    """
    Liste les modèles disponibles via l'API Gemini (inclut Gemma).
    
    Args:
        api_key: Clé API Google
        
    Returns:
        Liste de (model_id, display_name)
    """
    genai.configure(api_key=api_key)
    models = []
    
    try:
        for model in genai.list_models(page_size=100):
            # Vérifier que le modèle supporte generateContent (casse variable selon l'API)
            methods = getattr(model, 'supported_generation_methods', []) or []
            methods_lower = [m.lower() if m else '' for m in methods]
            if 'generatecontent' not in methods_lower:
                continue
            
            # Extraire l'ID (enlever le préfixe "models/")
            name = getattr(model, 'name', '') or ''
            model_id = name.replace('models/', '') if name.startswith('models/') else name
            
            display = getattr(model, 'display_name', None) or model_id
            
            models.append((model_id, f"{display} ({model_id})"))
        
        # Trier : Gemma et Gemini 3 en premier
        def sort_key(m):
            id_lower = m[0].lower()
            if 'gemma' in id_lower:
                return (0, id_lower)
            if 'gemini-3' in id_lower:
                return (1, id_lower)
            if 'gemini-2' in id_lower:
                return (2, id_lower)
            return (3, id_lower)
        
        models.sort(key=sort_key)
        return models
        
    except Exception as e:
        logger.error(f"Erreur listage modèles Gemini: {e}")
        raise


class GeminiAPI(APIConnector):
    """
    Connecteur pour l'API Gemini de Google.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", 
                 rate_limit: int = 60, timeout: int = 120):
        """
        Initialise le connecteur Gemini.
        
        Args:
            api_key: Clé API Google
            model: Modèle Gemini à utiliser
            rate_limit: Limite de requêtes par minute
            timeout: Timeout en secondes
        """
        super().__init__(api_key, rate_limit, timeout)
        self.model_name = model
        
        # Configurer l'API
        genai.configure(api_key=api_key)
        
        # Configuration de génération
        self.generation_config = {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        # Configuration de sécurité (permissive pour textes spécialisés)
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )

    def _extract_json_object(self, content: str, required_key: str = "") -> str:
        """
        Extrait de façon robuste le premier objet JSON valide dans une réponse texte.
        """
        stripped = content.strip()

        # Cas direct : la réponse est déjà du JSON propre
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        # Priorité aux blocs markdown explicites
        for fence in ("```json", "```"):
            if fence in content:
                json_start = content.find(fence) + len(fence)
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    candidate = content[json_start:json_end].strip()
                    if candidate.startswith("{") and candidate.endswith("}"):
                        return candidate

        # Recherche par équilibrage d'accolades, en ignorant les strings
        start = -1
        depth = 0
        in_string = False
        escaped = False

        for i, ch in enumerate(content):
            if ch == "\\" and not escaped:
                escaped = True
                continue

            if ch == '"' and not escaped:
                in_string = not in_string

            if not in_string:
                if ch == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "}" and depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        candidate = content[start:i + 1].strip()
                        try:
                            parsed = json.loads(candidate, strict=False)
                            if isinstance(parsed, dict) and (not required_key or required_key in parsed):
                                return candidate
                        except json.JSONDecodeError:
                            pass
            escaped = False

        # Fallback historique : dernier bloc entre première et dernière accolade
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return content[json_start:json_end]

        raise ValueError("Aucun objet JSON exploitable trouvé dans la réponse API")
    
    @retry(max_attempts=3)
    def translate_page(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Traduit une page via l'API Gemini.
        """
        self._rate_limit_wait()
        
        try:
            logger.info(f"Appel API Gemini (modèle: {self.model_name})")
            
            # LOG COMPLET : Prompt envoyé
            logger.info("=" * 80)
            logger.info("PROMPT SYSTÈME ENVOYÉ:")
            logger.info(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
            logger.info("-" * 80)
            logger.info("PROMPT UTILISATEUR ENVOYÉ:")
            logger.info(user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt)
            logger.info("=" * 80)
            
            # Gemini n'a pas de system prompt séparé, on combine
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            response = self.model.generate_content(full_prompt)
            
            # Extraire le texte
            content = response.text
            
            # LOG COMPLET : Réponse brute
            logger.info("=" * 80)
            logger.info("RÉPONSE BRUTE REÇUE:")
            logger.info(content)
            logger.info("=" * 80)
            
            # Extraire le JSON de façon robuste (évite de capter les {} du glossaire vide)
            json_content = self._extract_json_object(content, required_key="traduction")
            logger.debug("JSON extrait de la réponse Gemini")
            
            # Parser le JSON avec strict=False pour accepter les caractères de contrôle
            try:
                # Nettoyer les escapes invalides comme \> et \<
                json_content = json_content.replace('\\>', '>').replace('\\<', '<')
                
                # Parser avec strict=False pour accepter \n, \t, etc. dans les strings
                result = json.loads(json_content, strict=False)
                logger.info("Réponse JSON parsée avec succès")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de parsing JSON: {e}")
                logger.error(f"Contenu JSON extrait:\n{json_content[:1000]}...")
                raise
                    
        except Exception as e:
            logger.error(f"Erreur API Gemini: {e}")
            raise
    
    @retry(max_attempts=3)
    def consolidate_glossary(self, glossary: Dict[str, str],
                             prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Consolide le glossaire via Gemini.
        """
        self._rate_limit_wait()
        
        if prompt:
            full_prompt = prompt
        else:
            glossary_text = "\n".join([f"- {src}: {tgt}" for src, tgt in glossary.items()])
            full_prompt = f"""Tu es un expert en traduction terminologique.
Analyse le glossaire fourni et détecte les incohérences terminologiques.

Voici le glossaire actuel :

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
            response = self.model.generate_content(full_prompt)
            content = response.text
            
            json_content = self._extract_json_object(content, required_key="glossaire_consolidé")
            result = json.loads(json_content, strict=False)
            return result
            
        except Exception as e:
            logger.error(f"Erreur consolidation glossaire: {e}")
            raise
    
    @retry(max_attempts=3)
    def generate_summary(self, pages: List[str],
                         prompt: Optional[str] = None) -> str:
        """
        Génère un résumé via Gemini.
        """
        self._rate_limit_wait()
        
        if prompt:
            full_prompt = prompt
        else:
            pages_text = "\n\n---\n\n".join(pages)
            full_prompt = f"""Tu es un expert en synthèse de textes.
Résume de manière concise le contenu fourni.

Résume en 200 mots le contenu et l'argumentation de ces pages :

{pages_text}

Focus sur : concepts développés, thèses avancées, transitions argumentatives."""
        
        try:
            # Configuration pour résumé plus court
            summary_config = self.generation_config.copy()
            summary_config["max_output_tokens"] = 500
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=summary_config,
                safety_settings=self.safety_settings
            )
            
            response = model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Erreur génération résumé: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à l'API Gemini.
        """
        try:
            response = self.model.generate_content("Test")
            logger.info("Test de connexion Gemini réussi")
            return True
        except Exception as e:
            logger.error(f"Test de connexion Gemini échoué: {e}")
            return False
