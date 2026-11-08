"""
Orchestrateur principal de la traduction.
"""

import json
import logging
from typing import Dict, List, Callable, Optional
from pathlib import Path

from .api_connector import APIConnector
from .glossary import Glossary
from .context_manager import ContextManager

logger = logging.getLogger(__name__)


class Translator:
    """
    Orchestrateur principal qui coordonne la traduction, le glossaire et le contexte.
    """
    
    def __init__(self, api: APIConnector, glossary: Optional[Glossary],
                 context_mgr: ContextManager, prompts: Dict[str, str],
                 consolidation_freq: int = 50,
                 source_language: str = "source",
                 target_language: str = "cible",
                 use_glossary: bool = True):
        """
        Initialise le traducteur.
        
        Args:
            api: Connecteur API (Claude ou Gemini)
            glossary: Gestionnaire de glossaire
            context_mgr: Gestionnaire de contexte
            prompts: Templates de prompts
            consolidation_freq: Fréquence de consolidation du glossaire (en pages)
        """
        self.api = api
        self.glossary = glossary
        self.context = context_mgr
        self.prompts = prompts
        self.consolidation_freq = consolidation_freq
        self.source_language = source_language
        self.target_language = target_language
        self.use_glossary = use_glossary
        
        self.current_page = 0
        self.total_pages = 0
        self.is_paused = False
        self.should_stop = False
        
        logger.info("Translator initialisé")
    
    def translate_page(self, page_num: int, page_content: str, 
                      total_pages: int) -> Dict:
        """
        Traduit une page complète.
        
        Args:
            page_num: Numéro de la page
            page_content: Contenu source de la page
            total_pages: Nombre total de pages
            
        Returns:
            Dict avec:
                - traduction: str
                - termes_utilises: Dict[str, str]
                - nouveaux_termes: Dict[str, Dict]
                - page_num: int
        """
        logger.info(f"Traduction de la page {page_num}/{total_pages}")
        
        # 1. Assembler le contexte
        glossaire_json = "{}"
        if self.use_glossary and self.glossary:
            glossaire_json = json.dumps(
                self.glossary.get_all_terms(),
                ensure_ascii=False,
                indent=2
            )
        resume_contexte = self.context.get_context()

        # Blocs dynamiques du prompt selon activation du glossaire
        section_glossaire = ""
        instruction_glossaire = "**Terminologie** : garde une cohérence de traduction sur l'ensemble de la page."
        instruction_nouveaux_termes = "**Termes structurés** : retourne `termes_utilises` et `nouveaux_termes` vides (`{}`), sans texte additionnel."
        format_termes_utilises = "{}"
        format_nouveaux_termes = "{}"
        note_glossaire = "- Les champs `termes_utilises` et `nouveaux_termes` doivent rester vides (`{}`)."

        if self.use_glossary and self.glossary:
            section_glossaire = f"# Glossaire actuel\n{glossaire_json}\n"
            instruction_glossaire = "**Cohérence terminologique** : utilise STRICTEMENT les traductions du glossaire."
            instruction_nouveaux_termes = "**Nouveaux termes** : UNIQUEMENT pour les termes complexes ou ambigus."
            format_termes_utilises = "{\"terme_source\": \"terme_cible\", ...}"
            format_nouveaux_termes = (
                "{\"terme_source\": {\"traduction_proposee\": \"...\", "
                "\"contexte\": \"...\", \"justification\": \"...\"}}"
            )
            note_glossaire = (
                "- Si le glossaire est vide ({}), retourne `termes_utilises`: {}.\n"
                "- `nouveaux_termes` doit être vide ou contenir seulement 1-3 termes complexes max."
            )
        
        # 2. Formater les prompts avec les balises
        system_prompt = self.prompts["system_prompt"].format(
            glossaire_json=glossaire_json,
            resume_50_dernieres_pages=resume_contexte,
            langue_source=self.source_language,
            langue_cible=self.target_language,
            section_glossaire=section_glossaire,
            instruction_glossaire=instruction_glossaire,
            instruction_nouveaux_termes=instruction_nouveaux_termes,
            format_termes_utilises=format_termes_utilises,
            format_nouveaux_termes=format_nouveaux_termes,
            note_glossaire=note_glossaire
        )
        
        user_prompt = self.prompts["user_prompt"].format(
            numero=page_num,
            total_pages=total_pages,
            contenu_markdown_page=page_content
        )
        
        # 3. Appeler l'API
        try:
            result = self.api.translate_page(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Erreur lors de la traduction de la page {page_num}: {e}")
            raise
        
        # 4. Mettre à jour le glossaire
        # Nouveaux termes : ajouter au glossaire
        nouveaux_termes_ajoutes = 0
        if self.use_glossary and self.glossary:
            for terme_de, data in result.get("nouveaux_termes", {}).items():
                self.glossary.add_term(
                    terme_de=terme_de,
                    terme_fr=data.get("traduction_proposee", ""),
                    page=page_num,
                    context=data.get("contexte", ""),
                    note=data.get("justification", "")
                )
                nouveaux_termes_ajoutes += 1
        
        if nouveaux_termes_ajoutes > 0:
            logger.info(f"  → {nouveaux_termes_ajoutes} nouveau(x) terme(s) ajouté(s) au glossaire")
        
        # Termes utilisés : incrémenter fréquence SEULEMENT s'ils existent déjà
        termes_mis_a_jour = 0
        if self.use_glossary and self.glossary:
            for terme_de, terme_fr in result.get("termes_utilises", {}).items():
                if self.glossary.get_term(terme_de):  # Vérifier si le terme existe
                    self.glossary.update_frequency(terme_de, page_num)
                    termes_mis_a_jour += 1
        
        if termes_mis_a_jour > 0:
            logger.debug(f"  → {termes_mis_a_jour} terme(s) existant(s) mis à jour")
        
        # 5. Gérer le contexte glissant
        traduction = result.get("traduction", "")
        self.context.add_page(page_num, traduction)
        
        # Vérifier si un résumé doit être généré
        if self.context.should_generate_summary():
            logger.info("Génération d'un résumé contextuel...")
            pages_for_summary = self.context.get_pages_for_summary()
            try:
                pages_text = "\n\n---\n\n".join(pages_for_summary)
                summary_template = self.prompts.get("summary_prompt", "")
                if summary_template:
                    summary_prompt = summary_template.format(pages_recentes=pages_text)
                    summary = self.api.generate_summary(pages_for_summary, prompt=summary_prompt)
                else:
                    summary = self.api.generate_summary(pages_for_summary)
                self.context.add_summary(summary)
            except Exception as e:
                logger.error(f"Erreur lors de la génération du résumé: {e}")
                # Continuer même si le résumé échoue
        
        # 6. Retourner le résultat
        result["page_num"] = page_num
        return result
    
    def consolidate_glossary(self):
        """
        Consolide le glossaire pour détecter et corriger les incohérences.
        """
        logger.info("Consolidation du glossaire...")
        if not self.use_glossary or not self.glossary:
            logger.info("Consolidation ignorée (glossaire désactivé)")
            return
        
        try:
            glossary_dict = self.glossary.get_all_terms()
            glossary_text = "\n".join(
                [f"- {src}: {tgt}" for src, tgt in glossary_dict.items()]
            )
            consolidation_template = self.prompts.get("consolidation_prompt", "")
            if consolidation_template:
                consolidation_prompt = consolidation_template.format(
                    glossaire_recent=glossary_text
                )
                result = self.api.consolidate_glossary(
                    glossary_dict, prompt=consolidation_prompt
                )
            else:
                result = self.api.consolidate_glossary(glossary_dict)
            
            # Afficher les incohérences détectées
            incoherences = result.get("incohérences_détectées", [])
            if incoherences:
                logger.warning(f"{len(incoherences)} incohérence(s) détectée(s):")
                for inc in incoherences:
                    terme = inc.get("terme_source") or inc.get("terme_de", "?")
                    logger.warning(
                        f"  - {terme}: "
                        f"{inc.get('traductions_divergentes')} → "
                        f"{inc.get('traduction_recommandée')}"
                    )
            else:
                logger.info("Aucune incohérence détectée")
            
            # Appliquer le glossaire consolidé
            glossaire_consolide = result.get("glossaire_consolidé", {})
            if glossaire_consolide:
                self.glossary.consolidate(glossaire_consolide)
                logger.info(f"Glossaire consolidé: {len(glossaire_consolide)} termes")
            
        except Exception as e:
            logger.error(f"Erreur lors de la consolidation: {e}")
            # Ne pas interrompre la traduction pour une erreur de consolidation
    
    def run_translation(self, input_files: List[str], output_dir: str,
                       progress_callback: Optional[Callable] = None,
                       log_callback: Optional[Callable] = None,
                       page_completed_callback: Optional[Callable] = None):
        """
        Boucle principale de traduction.
        
        Args:
            input_files: Liste des fichiers markdown à traduire
            output_dir: Répertoire de sortie
            progress_callback: Fonction appelée pour mise à jour progression (current, total)
            log_callback: Fonction appelée pour logs (level, message)
            page_completed_callback: Fonction appelée après chaque page (num, source, translation)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.total_pages = len(input_files)
        self.current_page = 0
        self.should_stop = False
        
        if log_callback:
            log_callback("info", f"Démarrage de la traduction: {self.total_pages} pages")
        
        for i, input_file in enumerate(input_files, start=1):
            # Vérifier si on doit s'arrêter
            if self.should_stop:
                if log_callback:
                    log_callback("warning", "Traduction arrêtée par l'utilisateur")
                break
            
            # Vérifier si on est en pause
            while self.is_paused and not self.should_stop:
                import time
                time.sleep(0.5)
            
            if self.should_stop:
                break
            
            self.current_page = i
            
            # Vérifier si la page est déjà traduite
            output_file = output_path / f"page_{i:04d}.md"
            if output_file.exists():
                if log_callback:
                    log_callback("info", f"Page {i}/{self.total_pages} déjà traduite, passage à la suivante")
                
                # Mettre à jour la progression
                if progress_callback:
                    progress_callback(i, self.total_pages)
                
                # Charger la traduction existante pour le contexte
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_translation = f.read()
                    self.context.add_page(i, existing_translation)
                except Exception as e:
                    logger.warning(f"Impossible de charger la traduction existante pour le contexte: {e}")
                
                continue
            
            try:
                # Lire le fichier source
                page_content = self._read_text_file(input_file)
                
                # Ignorer les pages vides ou presque vides (moins de 10 caractères)
                if len(page_content.strip()) < 10:
                    if log_callback:
                        log_callback("info", f"Page {i}/{self.total_pages} vide ou trop courte, ignorée")
                    
                    # Créer un fichier vide pour marquer comme "traduit"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(page_content.strip())
                    
                    # Mettre à jour la progression
                    if progress_callback:
                        progress_callback(i, self.total_pages)
                    
                    continue
                
                if log_callback:
                    log_callback("info", f"Traduction page {i}/{self.total_pages}: {Path(input_file).name}")
                
                # Traduire la page
                result = self.translate_page(i, page_content, self.total_pages)
                
                # Sauvegarder la traduction
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result["traduction"])
                
                if log_callback:
                    log_callback("info", f"Page {i} traduite et sauvegardée")
                
                # Callback progression
                if progress_callback:
                    progress_callback(i, self.total_pages)
                
                # Callback page complétée
                if page_completed_callback:
                    page_completed_callback(i, page_content, result["traduction"])
                
                # Consolidation périodique du glossaire
                if self.use_glossary and self.glossary and i % self.consolidation_freq == 0:
                    if log_callback:
                        log_callback("info", f"Consolidation du glossaire (page {i})...")
                    self.consolidate_glossary()
                
            except Exception as e:
                error_msg = f"Erreur lors de la traduction de la page {i}: {str(e)}"
                logger.error(error_msg)
                if log_callback:
                    log_callback("error", error_msg)
                # Continuer avec la page suivante
        
        # Traduction terminée
        if not self.should_stop:
            if log_callback:
                log_callback("info", "Traduction terminée avec succès!")
            
            # Générer le fichier final assemblé
            self._assemble_final_translation(output_path, log_callback)
            
            # Exporter le glossaire final
            if self.use_glossary and self.glossary:
                self._export_final_glossary(output_path, log_callback)

    def _read_text_file(self, file_path: str) -> str:
        """
        Lit un fichier texte avec détection d'encodage robuste.
        """
        path = Path(file_path)
        raw = path.read_bytes()

        # Détection BOM explicite
        if raw.startswith(b"\xef\xbb\xbf"):
            return raw.decode("utf-8-sig")
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            return raw.decode("utf-16")
        if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
            return raw.decode("utf-32")

        # Fallbacks courants pour des fichiers markdown externes
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue

        # Dernier recours, remplace les bytes invalides pour ne pas bloquer la traduction
        logger.warning(f"Encodage non reconnu pour {file_path}, décodage avec remplacement")
        return raw.decode("utf-8", errors="replace")
    
    def _assemble_final_translation(self, output_path: Path, 
                                   log_callback: Optional[Callable] = None):
        """
        Assemble toutes les pages traduites en un seul fichier.
        
        Args:
            output_path: Répertoire de sortie
            log_callback: Fonction pour logs
        """
        try:
            final_file = output_path / "traduction_complete.md"
            
            with open(final_file, 'w', encoding='utf-8') as outf:
                # En-tête
                outf.write("# Traduction complète\n\n")
                outf.write("---\n\n")
                
                # Assembler toutes les pages
                page_files = sorted(output_path.glob("page_*.md"))
                for page_file in page_files:
                    with open(page_file, 'r', encoding='utf-8') as inf:
                        content = inf.read()
                        outf.write(content)
                        outf.write("\n\n---\n\n")
            
            if log_callback:
                log_callback("info", f"Traduction complète assemblée: {final_file}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'assemblage final: {e}")
            if log_callback:
                log_callback("error", f"Erreur assemblage: {str(e)}")
    
    def _export_final_glossary(self, output_path: Path,
                              log_callback: Optional[Callable] = None):
        """
        Exporte le glossaire final en JSON et CSV.
        
        Args:
            output_path: Répertoire de sortie
            log_callback: Fonction pour logs
        """
        try:
            # Export JSON
            json_file = output_path / "glossaire_final.json"
            self.glossary.export_json(str(json_file))
            
            # Export CSV
            csv_file = output_path / "glossaire_final.csv"
            self.glossary.export_csv(str(csv_file))
            
            if log_callback:
                log_callback("info", f"Glossaire exporté: {json_file}, {csv_file}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export du glossaire: {e}")
            if log_callback:
                log_callback("error", f"Erreur export glossaire: {str(e)}")
    
    def pause(self):
        """Met la traduction en pause."""
        self.is_paused = True
        logger.info("Traduction mise en pause")
    
    def resume(self):
        """Reprend la traduction."""
        self.is_paused = False
        logger.info("Traduction reprise")
    
    def stop(self):
        """Arrête la traduction."""
        self.should_stop = True
        logger.info("Arrêt de la traduction demandé")
    
    def get_progress(self) -> Dict:
        """
        Retourne l'état de progression.
        
        Returns:
            Dict avec current_page et total_pages
        """
        return {
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "is_paused": self.is_paused
        }
