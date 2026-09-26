# Tradomatic

Traducteur autonome de textes philosophiques allemands vers le français avec glossaire terminologique intelligent.

## Installation

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Utilisation

```bash
python src/main.py
```

## Configuration

1. **Paramètres** : Choisir API (Claude/Gemini), entrer clé API, tester connexion, définir chemins
2. **Prompts** : Personnaliser les prompts (balises : `{glossaire_json}`, `{numero}`, `{contenu_markdown_page}`)
3. **Traduction** : Lancer et suivre la progression
4. **Glossaire** : Visualiser les termes philosophiques en temps réel
5. **Comparaison** : Voir source et traduction côte à côte

## Glossaire

Le glossaire contient **uniquement les termes philosophiques complexes et concepts** identifiés automatiquement par le LLM dans la section `nouveaux_termes`, pas tous les mots du texte.

## Reprise automatique

- Le dernier projet est chargé automatiquement au démarrage
- Si la traduction est interrompue, elle reprend là où elle s'était arrêtée (pages déjà traduites sont ignorées)

## Logs

Tous les logs détaillés (prompts envoyés, réponses reçues, erreurs) sont dans :
- **Console** : Logs en temps réel
- **Fichier** : `logs/traduction_YYYYMMDD_HHMMSS.log` (logs complets)

## Structure

```
tradomatic/
├── src/
│   ├── core/      # API, glossaire, contexte, traduction
│   ├── ui/        # Interface PyQt6 (panneaux)
│   └── utils/     # i18n, config, logs
├── resources/     # Traductions UI, thèmes QSS
├── templates/     # Prompts par défaut
└── logs/          # Fichiers de log
```

## Coût

- **Gemini** : Gratuit (1500 req/jour)
- **Claude Sonnet 4** : ~43$ pour 700 pages

## Licence

MIT
