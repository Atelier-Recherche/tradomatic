"""
Script de test pour vérifier que tous les imports fonctionnent.
"""

import sys
from pathlib import Path

# Ajouter le répertoire au path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Test des imports de Tradomatic")
print("=" * 60)

try:
    # Core modules
    print("\n[Core modules]")
    from src.core.api_connector import APIConnector
    print("✓ api_connector")
    
    from src.core.claude_api import ClaudeAPI
    print("✓ claude_api")
    
    from src.core.gemini_api import GeminiAPI
    print("✓ gemini_api")
    
    from src.core.glossary import Glossary
    print("✓ glossary")
    
    from src.core.context_manager import ContextManager
    print("✓ context_manager")
    
    from src.core.translator import Translator
    print("✓ translator")
    
    from src.core.project import Project
    print("✓ project")
    
    # Utils modules
    print("\n[Utils modules]")
    from src.utils.i18n import I18n, get_i18n
    print("✓ i18n")
    
    from src.utils.logger import TranslationLogger, setup_logging
    print("✓ logger")
    
    from src.utils.config import Config, SecureStorage, get_config, get_secure_storage
    print("✓ config")
    
    # UI modules
    print("\n[UI modules]")
    from src.ui.main_window import MainWindow
    print("✓ main_window")
    
    from src.ui.settings_panel import SettingsPanel
    print("✓ settings_panel")
    
    from src.ui.prompts_panel import PromptsPanel
    print("✓ prompts_panel")
    
    from src.ui.translation_panel import TranslationPanel
    print("✓ translation_panel")
    
    from src.ui.comparison_panel import ComparisonPanel
    print("✓ comparison_panel")
    
    print("\n" + "=" * 60)
    print("✓ Tous les imports fonctionnent correctement !")
    print("=" * 60)
    
    # Test de base
    print("\n[Tests de base]")
    
    # Test i18n
    i18n = get_i18n("fr_FR")
    print(f"✓ i18n initialisé: {i18n.get_current_language_name()}")
    
    # Test config
    config = get_config()
    print(f"✓ Config initialisée: {config.get('api.provider')}")
    
    # Test project
    project = Project()
    print(f"✓ Project créé: {project.name}")
    
    # Test glossary (en mémoire)
    glossary = Glossary(":memory:")
    glossary.add_term("Test", "test", 1, "contexte test")
    term = glossary.get_term("Test")
    print(f"✓ Glossary fonctionne: {term['terme_fr']}")
    
    # Test context manager
    cm = ContextManager(window_size=5, pages_per_summary=10)
    cm.add_page(1, "contenu test")
    print(f"✓ ContextManager fonctionne: {cm.get_pages_count()} page(s)")
    
    print("\n" + "=" * 60)
    print("✓ Tous les tests de base réussis !")
    print("=" * 60)
    print("\nVous pouvez maintenant lancer l'application avec:")
    print("  Windows: run.bat")
    print("  Linux/Mac: ./run.sh")
    print()
    
except ImportError as e:
    print(f"\n✗ Erreur d'import: {e}")
    print("\nVérifiez que toutes les dépendances sont installées:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
