# evallm
Script python pour l'évaluation des llm avec des requêtes précises en mode batch où l'on peut tester sur plusieurs prompts, données, températures, graines, etc.

Ce script (que j'ai fait ce soir en 1H avec Cursor) permet de comparer les résultats de plusieurs LLM :
- vitesse de réponse avec ollama
- trop classe : variations sur plusieurs graines, températures, contextes, prompts, et prompts système (avec le nom que vous voulez!)
- comparaison des réponses visuellement dans la sortie
- préchauffage pour ne pas tenir compte du temps de chargement
- sortie en html sympa et en json
- fichier de configuration simple en json (ex : 9-9-99 où le llm doit deviner cette date à partir de phrases approximatives)

Pour importer les librairies, il suffit de regarder les imports au début du script.

Pour le lancer : python evallm.py 9-9-99.json
Dans ce Json le LLM doit deviner la date du 9/9/99 (mais elle n'est jamais dite précisément).

Les meilleurs modèles que j'ai testé pour faire cela et qui semblent équivalent, triés par vitesse (temps moyen) : 
- gemma2:latest (0.26s) 5.4 GB
- qwen2.5:14b (0.26s) 9.0 GB
- mistral-small:24b (0.31s) 14 GB
- gemma3:latest (0.45) 3.3 GB
- gemma3:12b (0.56) 8.1 GB
- deepseek-r1:14b (7.69s) 9.0 GB

Modèles qui ont échoué au test : 
- granite3.2:8b (incohérences selon la graine)
- llama3.2:latest
- moondream:latest
- qwen2.5-coder:3b
