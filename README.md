# StudyPlan

StudyPlan est une application pour organiser ses révisions : importer ses cours, noter ses échéances, préparer un planning et suivre sa progression.

## Prérequis

- Python installé sur l'ordinateur.
- PowerShell sous Windows.
- Git, si tu veux récupérer le projet ou envoyer tes changements.

Pour vérifier que Python est disponible :

```powershell
py --version
```

## Installer le projet

Ouvre PowerShell dans le dossier du projet (`Studyplan_app`), puis crée un environnement Python réservé au projet :

```powershell
py -m venv .venv
```

Installe les dépendances du frontend :

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\frontend\requirements.txt
```

L'environnement virtuel évite d'installer les bibliothèques de StudyPlan dans le reste de ton ordinateur.

## Lancer le frontend

Depuis la racine du projet, lance :

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\frontend\app.py
```

Streamlit affiche une adresse locale dans PowerShell et ouvre normalement le navigateur. Si le navigateur ne s'ouvre pas, copie l'adresse indiquée dans la console. Pour arrêter l'application, retourne dans PowerShell et appuie sur `Ctrl+C`.

## Mode démo et backend

Sans configuration supplémentaire, le frontend démarre en **mode démo** avec des données fictives. Ces données sont temporaires : elles ne sont pas sauvegardées dans une base de données et peuvent disparaître quand la session se termine.

Pour connecter le frontend à un backend FastAPI déjà démarré, renseigne son adresse dans la même fenêtre PowerShell avant de lancer Streamlit. Exemple si le backend écoute sur le port 8000 :

```powershell
$env:STUDYPLAN_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m streamlit run .\frontend\app.py
```

## Pages du frontend

- **Accueil** : présentation de StudyPlan.
- **Cours** : importer un support PDF ou Markdown et consulter ses cours.
- **Échéances** : ajouter et consulter les examens et rendus.
- **Planning** : saisir ses disponibilités, générer des séances et télécharger le calendrier `.ics`.
- **Dashboard** : voir l'avancement, les séances et les prochaines échéances.

## Structure du frontend

```text
frontend/
├── app.py
├── api_client.py
├── mock_data.py
├── requirements.txt
└── pages/
    ├── Cours.py
    ├── Échéances.py
    ├── Planning.py
    └── Dashboard.py
```

- `app.py` lance la page d'accueil.
- `api_client.py` regroupe les appels au backend.
- `mock_data.py` fournit les données utilisées en mode démo.
- `pages/` contient les différentes pages Streamlit.
- `requirements.txt` liste les bibliothèques nécessaires au frontend.
