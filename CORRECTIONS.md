# Corrections apportées

## 1. ✅ Erreur High DPI (PyQt6)

**Problème** : `AttributeError: type object 'ApplicationAttribute' has no attribute 'AA_EnableHighDpiScaling'`

**Solution** : Supprimé les attributs High DPI qui ne sont plus nécessaires dans PyQt6 (activés par défaut).

**Fichier** : `src/main.py`

## 2. ✅ Changement de prompt ne fonctionnait pas

**Problème** : Quand on changeait de prompt dans le sélecteur, l'éditeur affichait toujours le même contenu. Seules les balises disponibles changeaient.

**Solution** : 
- Ajout d'un flag `_loading` pour éviter les sauvegardes pendant le chargement initial
- Blocage des signaux pendant la mise à jour du texte pour éviter les boucles
- Correction de la logique dans `on_prompt_changed()`

**Fichier** : `src/ui/prompts_panel.py`

## 3. ✅ Scan des modèles disponibles

**Problème** : Pas de sélecteur de modèles après avoir testé la connexion API.

**Solution** : 
- Ajout d'un `QComboBox` pour sélectionner le modèle
- Remplissage automatique après test de connexion réussi
- Liste des modèles disponibles :
  - **Claude** : claude-sonnet-4, claude-3-5-sonnet, claude-3-opus
  - **Gemini** : gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash

**Fichier** : `src/ui/settings_panel.py`

## 4. ✅ Clarification paramètres de traduction

**Problème** : Confusion entre les paramètres de traduction et les prompts.

**Solution** : Ajout d'une note explicative dans le panneau Paramètres :

> ℹ️ Ces paramètres contrôlent la logique de traduction (fréquence des consolidations, résumés, etc.). Pour modifier le contenu des prompts, allez dans l'onglet Prompts.

**Fichier** : `src/ui/settings_panel.py`

## Résumé des changements

### Paramètres de traduction (onglet Paramètres)
Ces paramètres contrôlent **QUAND** les actions se produisent :
- **Consolidation tous les X pages** : Quand harmoniser le glossaire
- **Résumé tous les X pages** : Quand générer un résumé contextuel
- **Fenêtre contexte** : Combien de résumés garder en mémoire
- **Checkpoint tous les X pages** : Quand sauvegarder l'état

### Prompts (onglet Prompts)
Les prompts contrôlent **COMMENT** les actions se font :
- **Prompt système** : Instructions générales pour le LLM
- **Prompt utilisateur** : Format de la requête de traduction
- **Prompt consolidation** : Comment détecter les incohérences
- **Prompt résumé** : Comment générer les résumés

## Pour tester

1. Relancer l'application :
   ```bash
   python src\main.py
   ```

2. Aller dans **Paramètres** :
   - Entrer une clé API
   - Cliquer sur "Tester la connexion"
   - → Le sélecteur de modèles devrait se remplir

3. Aller dans **Prompts** :
   - Changer de prompt dans le sélecteur
   - → Le contenu de l'éditeur devrait changer
   - → Les balises disponibles devraient changer

4. Vérifier la note explicative dans **Paramètres** > **Paramètres de traduction**
