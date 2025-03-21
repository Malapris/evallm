# evallm
Script python pour l'évaluation des llm avec des requêtes précises en mode batch où l'on peut tester sur plusieurs prompts, données, températures, graines, etc.

Ce script (que j'ai fait ce soir en 1H avec Cursor) permet de comparer les résultats de plusieurs LLM :
- vitesse de réponse avec ollama
- [V3.0] lecture de fichiers pour les prompts système et utilisateur ainsi que le contexte (voir exemple dans merge-test-01)
- trop classe : variations sur plusieurs graines, températures, contextes, prompts, et prompts système (avec le nom que vous voulez!)
- comparaison des réponses visuellement dans la sortie
- préchauffage pour ne pas tenir compte du temps de chargement
- sortie en html sympa et en json [V3.0] : amélioration de la sortie html
- fichier de configuration simple en json (ex : 9-9-99 où le llm doit deviner cette date à partir de phrases approximatives)

Présentation
![image](https://github.com/user-attachments/assets/b373ca38-4911-4d4c-b15d-e97743717f29)

Synthèse des résultats en temps de réponse et tokens
![image](https://github.com/user-attachments/assets/94d67346-2865-4405-a84e-d42be7478b59)


Librairies nécessaires : 
ollama>=0.1.6
json-repair>=0.2.0
tqdm>=4.65.0

Pour le lancer : python evallm.py 9-9-99.json # exemple avec le test de base
Dans ce Json le LLM doit deviner la date du 9/9/99 (mais elle n'est jamais dite précisément).

Les meilleurs modèles que j'ai testé pour faire cela, triés par vitesse (temps moyen) et taille : 
- mistral-small:24b (0.31s) 14 GB
- gemma3:12b (0.56s) 8.1 GB
- omercelik/reka-flash-3 (12.12s) 13 GB

Modèles qui ont échoué au niveau "hard" : 
- gemma2:latest (0.26s) 5.4 GB
- qwen2.5:14b (0.26s) 9.0 GB
- technobyte/Llama-3.3-70B-Abliterated:IQ2_XXS (0.46s) 19GB
- deepseek-r1:14b (7.69s) 9.0 GB
- mistral-nemo:12b (0.11s) 7.1 GB
- gemma3:latest (0.45s) 3.3 GB
- openthinker:7b (2.68s) 4.7 GB
- deepscaler:latest (6.17s) 3.6 GB

Modèles qui ont échoué au test de base : 
- granite3.2:8b (incohérences selon la graine)
- llama3.2:latest
- moondream:latest
- qwen2.5-coder:3b
- stablelm2:1.6b
