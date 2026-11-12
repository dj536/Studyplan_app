# Instructions pour Copilot

## À propos du projet

StudyPlan est une application en français pour organiser les révisions : consulter des cours, gérer des échéances, créer un planning et suivre sa progression.

## Technologies et structure

- Le frontend est développé en Python avec Streamlit.
- `frontend/app.py` lance l’application.
- `frontend/api_client.py` regroupe les appels au backend.
- `frontend/mock_data.py` fournit les données du mode démo.
- `frontend/pages/` contient les pages Cours, Échéances, Planning et Dashboard.
- Le backend, lorsqu’il est utilisé, est une API FastAPI configurée avec `STUDYPLAN_API_URL`.
- Sans cette configuration, l’application fonctionne en mode démo.

## Consignes de développement

- Suivre les conventions et la structure déjà présentes dans le projet.
- Garder l’interface et les messages destinés aux utilisateurs en français.
- Réutiliser les fonctions et composants existants avant d’en créer de nouveaux.
- Préserver le fonctionnement du mode démo lorsque le frontend est modifié.
- Ne pas ajouter de dépendance sans nécessité ; mettre à jour le fichier de dépendances correspondant si besoin.
- Ne pas inclure de secrets, de données personnelles ou de fichiers de cours réels dans le code.
- Vérifier les tests disponibles après une modification et expliquer comment lancer ou tester le changement.
- Ne pas modifier des fichiers sans rapport avec la demande.
