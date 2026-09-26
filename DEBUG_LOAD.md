# Debug du chargement de projet

## Problème 1 : Changement de prompt ne fonctionne pas

**Cause** : Le prompt n'était pas sauvegardé avant de changer de sélection.

**Solution appliquée** :
- Ajout d'une variable `_current_prompt_key` pour tracker le prompt actuel
- Dans `on_prompt_changed()`, sauvegarde du prompt actuel AVANT de charger le nouveau
- Logs ajoutés pour débugger

**Test** :
1. Ouvrir l'onglet Prompts
2. Modifier le texte du "Prompt système"
3. Changer vers "Prompt utilisateur (page)"
4. Revenir à "Prompt système"
5. ✅ Tes modifications devraient être conservées

## Problème 2 : Chemins non chargés

**Diagnostic** :
- Le code de chargement est correct (lignes 363-364 de settings_panel.py)
- Ton fichier `projet.json` a des chemins vides :
  ```json
  "paths": {
    "input_directory": "",
    "output_directory": "",
  ```

**Causes possibles** :
1. Tu n'as pas rempli les chemins dans l'interface avant de sauvegarder
2. Le `save_to_project()` n'a pas été appelé

**Solution** :
- Quand tu sauvegardes un projet, le code appelle `save_to_project()` qui récupère les valeurs des champs
- Si les champs sont vides dans l'UI, ils seront vides dans le JSON

**Test** :
1. Ouvrir ton projet
2. Aller dans Paramètres
3. Remplir "Dossier d'entrée" et "Dossier de sortie"
4. Sauvegarder le projet (Ctrl+S)
5. Fermer et rouvrir le projet
6. ✅ Les chemins devraient être chargés

## Problème 3 : Modèles Gemini/Gemma

**Solution appliquée** :
- Scan dynamique via `genai.list_models()`
- Filtre pour les modèles supportant `generateContent`
- Inclut Gemma 3 (27B, 12B, 4B, 1B)
- Inclut Gemini 3 Flash, Gemini 3 Pro, etc.

**Test** :
1. Onglet Paramètres
2. Entrer clé API Google
3. Cliquer "Tester la connexion"
4. ✅ La liste déroulante devrait se remplir avec tous les modèles (Gemma + Gemini)

## Vérification rapide

Ouvre ton `projet.json` et vérifie :
```json
{
  "paths": {
    "input_directory": "D:/ton/chemin/input",  // ← Doit être rempli
    "output_directory": "D:/ton/chemin/output", // ← Doit être rempli
  },
  "api_settings": {
    "model": "gemma-3-27b-it"  // ← Sera rempli après avoir testé et sélectionné
  }
}
```

Si les chemins sont vides, c'est normal - tu dois les remplir dans l'interface et sauvegarder à nouveau.
