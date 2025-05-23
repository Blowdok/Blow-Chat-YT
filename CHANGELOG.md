# Changelog

## [2.0.1] - 2025-05-01

### Ajouté

- Support de l'authentification Hugging Face pour les modèles sentence-transformers
- Champ `huggingface_token` dans la section [API_KEYS] du fichier config.ini
- Option pour ajouter le token Hugging Face via l'interface graphique (menu Paramètres > Paramètres)
- Méthode `init_huggingface_auth()` pour initialiser l'authentification avec Hugging Face
- Méthode `update_huggingface_token()` pour mettre à jour le token d'authentification
- Mise à jour de la documentation avec des instructions pour obtenir et configurer un token Hugging Face
- Section "Résolution des problèmes d'authentification Hugging Face" dans le README

### Modifié

- Amélioration de la gestion des erreurs lors du chargement des modèles sentence-transformers
- Mise à jour du fichier `requirements.txt` pour inclure `huggingface_hub`
- Amélioration des méthodes `create_vector_database` et `enrich_vector_database` pour une meilleure gestion des erreurs d'authentification

### Corrigé

- Résolution de l'erreur "401 Client Error: Unauthorized" lors du téléchargement des modèles sentence-transformers (problème signalé par @xerexesx)
- Amélioration de la gestion des exceptions dans les méthodes liées à l'utilisation des bases de données vectorielles
- Correction du problème de persistance du token Hugging Face qui s'effaçait à chaque fermeture de l'application

### Remerciements

- Merci à [@xerexesx](https://github.com/xerexesx) pour avoir signalé le problème d'authentification Hugging Face et proposé une solution

## [2.0.0] - 2025-04-01

### Ajouté

- Architecture modulaire plus robuste
- Possibilité de créer des bases de données vectorielles indépendantes
- Fonction d'enrichissement dynamique des bases existantes
- Sélection de dossiers sources personnalisés pour vos documents
- Affichage d'informations détaillées sur chaque base de données
- Réglage de la taille des chunks via l'interface
- Sélection simplifiée des bases via menu déroulant

### Modifié

- Refonte complète de l'architecture pour améliorer la maintenabilité
- Optimisation de la gestion des erreurs

## [1.1.0] - 2025-03-15

### Ajouté

- Version initiale publiée sur GitHub
- Interface graphique CustomTkinter
- Support des API Groq et YouTube
- Fonctionnalités d'analyse de vidéos YouTube
- Base de données vectorielle avec FAISS
- Personnalisation de l'interface
