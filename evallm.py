import ollama
import json
import json_repair
import time
import os
import webbrowser
import logging
from datetime import datetime
from tqdm import tqdm
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_json_filename(html_filename):
    """Retourne le nom du fichier JSON correspondant au fichier HTML."""
    return os.path.splitext(os.path.basename(html_filename))[0] + ".json"

def extract_model_names(ollama_response):
    """
    Extrait les noms des modèles à partir de la réponse d'ollama.list()
    
    Args:
        ollama_response: La réponse d'ollama.list() contenant l'attribut models
        
    Returns:
        list: Liste des noms de modèles
    """
    model_names = []
    if hasattr(ollama_response, 'models'):
        for model in ollama_response.models:
            if hasattr(model, 'model'):
                model_names.append(model.model)
    logger.debug(f"Modèles extraits : {model_names}")
    return model_names

def generate_html_report(results, output_file):
    """Génère un rapport HTML avec des tableaux de comparaison des réponses LLM."""
    
    json_filename = get_json_filename(output_file)
    
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comparaison de LLM avec Ollama</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; background-color: #f8f9fa; }
            h1 { color: #1a237e; text-align: center; margin-bottom: 30px; }
            h2 { color: #283593; margin-top: 40px; border-bottom: 1px solid #c5cae9; padding-bottom: 10px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 30px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
            th, td { border: 1px solid #e0e0e0; padding: 12px; text-align: left; vertical-align: top; }
            th { background-color: #e8eaf6; font-weight: bold; color: #1a237e; }
            tr:nth-child(even) { background-color: #f5f5f5; }
            tr:hover { background-color: #e8eaf6; }
            .model-header { background-color: #3f51b5; color: white; }
            .response { max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
            .metadata { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
            .summary-table th { text-align: center; }
            .footer { text-align: center; margin-top: 50px; font-size: 0.8em; color: #5c6bc0; }
            .temp-badge { display: inline-block; background-color: #5c6bc0; color: white; padding: 2px 6px; 
                          border-radius: 3px; font-size: 0.8em; margin-left: 8px; }
            .json-link { display: block; text-align: right; margin: 10px 0; color: #3f51b5; text-decoration: none; }
            .json-link:hover { text-decoration: underline; }
            .models-list { background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0; 
                          box-shadow: 0 1px 3px rgba(0,0,0,0.12); font-family: monospace; }
        </style>
    </head>
    <body>
        <h1>Comparaison de Modèles LLM avec Ollama</h1>
        <a href=\"""" + json_filename + """\" class="json-link">📊 Voir les données brutes (JSON)</a>
        <div class="metadata">
            <p><strong>Date de génération:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>

        <h2>Modèles Disponibles</h2>
        <div class="models-list">
            """ + json.dumps(extract_model_names(ollama.list())) + """
        </div>
    """

    # Regrouper les résultats par combinaison
    combinations = {}
    for result in results:
        key = (result["system_prompt_id"], result["user_prompt_id"], result["context_id"], 
               result["seed"], result["temperature"])
        if key not in combinations:
            combinations[key] = []
        combinations[key].append(result)

    # Synthèse des temps de réponse
    model_temp_times = {}
    for result in results:
        model = result["model"]
        temp = result["temperature"]
        key = f"{model} (temp={temp})"
        if key not in model_temp_times:
            model_temp_times[key] = []
        model_temp_times[key].append(result["response_time"])
    
    # Tableau de synthèse
    html += """
    <h2>Synthèse des Performances</h2>
    <table class="summary-table">
        <tr class="model-header">
            <th>Modèle</th>
            <th>Temps moyen (s)</th>
            <th>Temps minimum (s)</th>
            <th>Temps maximum (s)</th>
            <th>Nombre de tokens moyen</th>
        </tr>
    """
    
    for model_temp, times in sorted(model_temp_times.items()):
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        # Extraire modèle et température
        model = model_temp.split(" (temp=")[0]
        temp = model_temp.split("=")[1][:-1]
        
        # Calcul approximatif de tokens (pourrait être remplacé par une mesure plus précise)
        avg_tokens = sum(len(r["response"].split()) for r in results 
                         if r["model"] == model and r["temperature"] == float(temp)) / len(times)
        
        html += f"""
        <tr>
            <td>{model} <span class="temp-badge">temp={temp}</span></td>
            <td>{avg_time:.2f}</td>
            <td>{min_time:.2f}</td>
            <td>{max_time:.2f}</td>
            <td>{avg_tokens:.0f}</td>
        </tr>
        """
    
    html += """
    </table>
    """

    # Tableaux de comparaison pour chaque combinaison
    html += """
    <h2>Résultats Détaillés</h2>
    <table>
        <tr class="model-header">
            <th>Modèle</th>
            <th>Système</th>
            <th>Prompt</th>
            <th>Contexte</th>
            <th>Graine</th>
            <th>Température</th>
            <th>Temps (s)</th>
            <th>Réponse</th>
        </tr>
    """
    
    # Trier les résultats par modèle, système, prompt, contexte, graine et température
    sorted_results = sorted(results, key=lambda x: (
        x["model"], 
        x["system_prompt_id"], 
        x["user_prompt_id"], 
        x["context_id"],
        x["seed"],
        x["temperature"]
    ))
    
    for result in sorted_results:
        # Remplacer les sauts de ligne pour un affichage HTML correct
        response_html = result["response"].replace("\n", "<br>")
        
        html += f"""
        <tr>
            <td>{result["model"]}</td>
            <td>{result["system_prompt_id"]}</td>
            <td>{result["user_prompt_id"]}</td>
            <td>{result["context_id"]}</td>
            <td>{result["seed"]}</td>
            <td>{result["temperature"]}</td>
            <td>{result["response_time"]:.2f}</td>
            <td class="response">{response_html}</td>
        </tr>
        """
    
    html += """
    </table>
    """

    html += """
        <div class="footer">
            <p>Généré avec le script de comparaison LLM pour Ollama</p>
        </div>
    </body>
    </html>
    """
    
    return html

def warmup_model(model, system_prompt, user_prompt, context=""):
    """Préchauffage du modèle avec une graine 0."""
    logger.info(f"Préchauffage du modèle {model}...")
    full_prompt = f"{context}\n\n{user_prompt}" if context else user_prompt
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        ollama.chat(
            model=model,
            messages=messages,
            options={
                "seed": 0,
                "temperature": 0.7
            }
        )
        logger.info(f"Préchauffage réussi pour {model}")
    except Exception as e:
        logger.warning(f"Avertissement lors du préchauffage de {model}: {e}")

def compare_llms(config_file, output_file=None):
    """Compare différents LLM en utilisant Ollama selon la configuration spécifiée."""
    
    logger.info(f"Chargement de la configuration depuis {config_file}")
    # Charger la configuration depuis le fichier JSON
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json_repair.load(f)
    
    # Déterminer le nom du fichier de sortie basé sur le fichier d'entrée
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(config_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_{timestamp}.html"
        logger.info(f"Fichier de sortie automatiquement défini : {output_file}")
    
    models = config.get("models", [])
    system_prompts = config.get("system_prompts", {})
    user_prompts = config.get("user_prompts", {})
    contexts = config.get("contexts", {})
    seeds = config.get("seeds", [42])
    temperatures = config.get("temperatures", [0.7])

    logger.info(f"Configuration chargée : {len(models)} modèles, {len(system_prompts)} prompts système, "
                f"{len(user_prompts)} prompts utilisateur, {len(contexts)} contextes")
    
    # Vérifier que les modèles sont disponibles dans Ollama
    try:
        logger.info("Vérification des modèles disponibles...")
        available_models_response = ollama.list()
        available_models = extract_model_names(available_models_response)
        
        for model in models:
            if model not in available_models:
                logger.warning(f"Le modèle '{model}' n'est pas disponible. Utilisez 'ollama pull {model}' pour le télécharger.")
                
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des modèles: {e}")
        logger.error("Assurez-vous qu'Ollama est installé et en cours d'exécution.")
        return []
    
    # Calculer le nombre total d'itérations
    total_iterations = len(models) * len(system_prompts) * len(user_prompts) * len(contexts) * len(seeds) * len(temperatures)
    logger.info(f"Nombre total d'itérations à effectuer : {total_iterations}")
    results = []
    
    # Générer les réponses pour chaque combinaison
    with tqdm(total=total_iterations, desc="Génération des réponses") as pbar:
        current_model = None
        for model in models:
            # Préchauffer le modèle si on change de modèle
            if current_model != model:
                logger.info(f"Changement de modèle : passage à {model}")
                # Utiliser le premier prompt système et utilisateur disponible pour le préchauffage
                first_sys_prompt = next(iter(system_prompts.values()))
                first_user_prompt = next(iter(user_prompts.values()))
                first_context = next(iter(contexts.values()))
                warmup_model(model, first_sys_prompt, first_user_prompt, first_context)
                current_model = model

            for sys_id, system_prompt in system_prompts.items():
                for prompt_id, user_prompt in user_prompts.items():
                    for ctx_id, context in contexts.items():
                        for seed in seeds:
                            for temperature in temperatures:
                                logger.debug(f"Génération pour {model} (seed={seed}, temp={temperature})")
                                # Construire le prompt complet avec contexte si nécessaire
                                full_prompt = user_prompt
                                if context:
                                    full_prompt = f"{user_prompt}\n\n{context}"
                                
                                # Générer la réponse avec Ollama
                                start_time = time.time()
                                try:
                                    messages = [
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": full_prompt}
                                    ]
                                    
                                    response = ollama.chat(
                                        model=model,
                                        messages=messages,
                                        options={
                                            "seed": seed if seed is not None else None,
                                            "temperature": temperature
                                        }
                                    )
                                    
                                    elapsed_time = time.time() - start_time
                                    logger.debug(f"Réponse générée en {elapsed_time:.2f}s")
                                    
                                    # Enregistrer les détails de la réponse
                                    result = {
                                        "model": model,
                                        "system_prompt": system_prompt,
                                        "system_prompt_id": sys_id,
                                        "user_prompt": user_prompt,
                                        "user_prompt_id": prompt_id,
                                        "context": context,
                                        "context_id": ctx_id,
                                        "seed": seed,
                                        "temperature": temperature,
                                        "response": response["message"]["content"],
                                        "response_time": elapsed_time
                                    }
                                except Exception as e:
                                    logger.error(f"Erreur avec {model} (temp={temperature}): {e}")
                                    result = {
                                        "model": model,
                                        "system_prompt": system_prompt,
                                        "system_prompt_id": sys_id,
                                        "user_prompt": user_prompt,
                                        "user_prompt_id": prompt_id,
                                        "context": context,
                                        "context_id": ctx_id,
                                        "seed": seed,
                                        "temperature": temperature,
                                        "response": f"ERREUR: {str(e)}",
                                        "response_time": time.time() - start_time
                                    }
                                
                                results.append(result)
                                pbar.update(1)
    
    logger.info("Génération des réponses terminée")
    
    # Générer et sauvegarder le rapport HTML
    logger.info("Génération du rapport HTML...")
    html_content = generate_html_report(results, output_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Rapport HTML sauvegardé dans {output_file}")
    
    # Sauvegarder les données brutes en JSON pour d'éventuelles analyses ultérieures
    json_output = get_json_filename(output_file)
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Données brutes sauvegardées dans {json_output}")
    
    # Ouvrir le fichier HTML dans le navigateur par défaut
    webbrowser.open('file://' + os.path.abspath(output_file))
    logger.info("Rapport ouvert dans le navigateur")
    
    return results

def main():
    """Fonction principale pour exécuter le script depuis la ligne de commande."""
    parser = argparse.ArgumentParser(description="Comparer des LLM avec Ollama et générer un rapport HTML")
    parser.add_argument("config", help="Fichier de configuration JSON")
    parser.add_argument("--output", "-o", help="Fichier de sortie HTML (optionnel)")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    compare_llms(args.config, args.output)

if __name__ == "__main__":
    main()
