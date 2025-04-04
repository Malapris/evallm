import ollama
import json
import json_repair
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.logging import RichHandler
from pydantic import BaseModel
import logging
import platform
import psutil
import GPUtil
import sys
import webbrowser
import shutil
import requests
from jinja2 import Environment, FileSystemLoader

# Constantes
DEFAULT_OLLAMA_URL = 'http://localhost:11434'
OLLAMA_API_URL = f"{DEFAULT_OLLAMA_URL}/api/version"
EVALLM_VERSION = "4.0.0"
GB_DIVISOR = 1024**3

size = shutil.get_terminal_size()

# Configuration du logging avec rich
console = Console(
    width=size.columns,
    force_terminal=True,
    force_interactive=True,
    color_system="auto",
    legacy_windows=False
)

# Configuration de l'encodage pour Windows
if platform.system() == 'Windows':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(
        rich_tracebacks=True,
        console=console,
        markup=True,
        show_time=True,
        show_path=False
    )]
)
logger = logging.getLogger("evallm")

# Configuration de la barre de progression
progress_columns = [
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(bar_width=None),
    TaskProgressColumn(),
    TimeRemainingColumn(),
]

@dataclass
class SystemInfo:
    os: str
    os_version: str
    python_version: str
    ollama_version: str
    evallm_version: str
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    gpu: Optional[List[Dict[str, Any]]]
    hostname: str

class ModelConfig(BaseModel):
    models: List[str]
    system_prompts: Dict[str, str]
    user_prompts: Dict[str, str]
    contexts: Dict[str, str]
    seeds: List[int] = [42]
    temperatures: List[float] = [0.7]
    commentaire: str = ""
    resultats: List[str] = []

class Result(BaseModel):
    model: str
    system_prompt: str
    system_prompt_id: str
    user_prompt: str
    user_prompt_id: str
    context: str
    context_id: str
    seed: int
    temperature: float
    response: str
    response_time: float
    commentaire: str
    Resultats: Optional[List[str]] = None

# Template HTML intégré
HTML_TEMPLATE = r"""
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
        .results-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.12); table-layout: fixed; }
        .results-table th, .results-table td { border: 1px solid #e0e0e0; padding: 12px; text-align: left; vertical-align: top; }
        .results-table th { background-color: #e8eaf6; font-weight: bold; color: #1a237e; }
        .results-table tr:nth-child(even) { background-color: #f5f5f5; }
        .results-table tr:hover { background-color: #e8eaf6; }
        .model-header { background-color: #3f51b5; color: white; }
        .response { max-height: 300px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; }
        .response-content { padding: 10px; background-color: #f8f9fa; border-radius: 4px; cursor: pointer; }
        .response-content:hover { background-color: #e8eaf6; }
        .response-pre { 
            display: none; 
            position: fixed; 
            top: 5%; 
            left: 5%; 
            width: 90%; 
            max-height: 90vh;
            background-color: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-y: auto; 
            z-index: 1000; 
        }
        .response-pre pre { 
            margin: 0; 
            white-space: pre-wrap; 
            font-family: monospace;
            font-size: 14px;
            line-height: 1.4;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            max-height: none;
            overflow: visible;
        }
        .response-pre .think-section { color: #666; font-style: italic; }
        .think-tag { color: #5c6bc0; font-weight: bold; }
        .response-text { white-space: pre-wrap; }
        .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                  background-color: rgba(0,0,0,0.5); z-index: 999; }
        .close-button { position: absolute; top: 10px; right: 10px; cursor: pointer; font-size: 24px; }
        .metadata { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .summary-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .summary-table th, .summary-table td { border: 1px solid #e0e0e0; padding: 12px; text-align: center; }
        .summary-table th { background-color: #3f51b5; color: white; font-weight: bold; }
        .summary-table tr:nth-child(even) { background-color: #f5f5f5; }
        .summary-table tr:hover { background-color: #e8eaf6; }
        .footer { text-align: center; margin-top: 50px; font-size: 0.8em; color: #5c6bc0; }
        .temp-badge { display: inline-block; background-color: #5c6bc0; color: white; padding: 2px 6px; 
                      border-radius: 3px; font-size: 0.8em; margin-left: 8px; }
        .json-link { display: block; text-align: right; margin: 10px 0; color: #3f51b5; text-decoration: none; }
        .json-link:hover { text-decoration: underline; }
        .models-list { background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0; 
                      box-shadow: 0 1px 3px rgba(0,0,0,0.12); font-family: monospace; }
        .input-data { background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;
                      box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .input-content { white-space: pre-wrap; background-color: #f5f5f5; padding: 10px; border-left: 4px solid #3f51b5; margin: 10px 0; }
        .commentaire { background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;
                      box-shadow: 0 1px 3px rgba(0,0,0,0.12); font-style: italic; }
        .highlighted-response { text-decoration: underline; text-decoration-color: green; text-decoration-thickness: 2px; }
        .system-info { background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;
                      box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .system-info h3 { color: #1a237e; margin-top: 0; }
        .system-info table { margin: 10px 0; width: 100%; }
        .system-info td:first-child { font-weight: bold; width: 200px; }
        .identical { color: #666; font-style: italic; }
        .think-section { color: #666; font-style: italic; }
        think { display: block; color: #666; font-style: italic; margin: 5px 0; }
        @media screen and (max-width: 768px) {
            .results-table { display: block; overflow-x: auto; }
            .summary-table { display: block; overflow-x: auto; }
        }
        .header-info {
            text-align: center;
            margin-bottom: 20px;
            color: #5c6bc0;
            font-size: 1.2em;
        }
    </style>
    <script>
        function showResponse(response, event) {
            event.preventDefault();
            const pre = document.createElement('pre');
            // Décodage de l'encodage JSON
            try {
                response = JSON.parse('"' + response + '"');
            } catch (e) {
                // Si le décodage échoue, on garde la réponse originale
            }
            // Échappement des caractères spéciaux et gestion des sauts de ligne
            const escapedResponse = response
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;')
                .replace(/\n/g, '<br>')
                .replace(/\r/g, '');
            pre.innerHTML = escapedResponse;
            const div = document.createElement('div');
            div.className = 'response-pre';
            div.innerHTML = '<span class="close-button" onclick="closeResponse()">&times;</span>';
            div.appendChild(pre);
            document.body.appendChild(div);
            document.querySelector('.overlay').style.display = 'block';
            div.style.display = 'block';
        }
        
        function closeResponse() {
            const pre = document.querySelector('.response-pre');
            if (pre) {
                pre.remove();
            }
            document.querySelector('.overlay').style.display = 'none';
        }
        
        // Fermer avec la touche Escape
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeResponse();
            }
        });
        
        // Fermer en cliquant sur l'overlay
        document.querySelector('.overlay').addEventListener('click', closeResponse);
    </script>
</head>
<body>
    <div class="overlay"></div>
    <h1>evallm : comparaison de modèles avec ollama</h1>
    <div class="header-info">
        <h2>{{ system_info.hostname }} - {{ system_info.os }} {{ system_info.os_version }} - {{ datetime.now().strftime("%d/%m/%Y %H:%M:%S") }}</h2>
    </div>

    <div class="system-info">
        <h3>Informations Système</h3>
        <table>
            <tr>
                <td>Nom de la machine</td>
                <td>{{ system_info.hostname }}</td>
            </tr>
            <tr>
                <td>Système d'exploitation</td>
                <td>{{ system_info.os }} {{ system_info.os_version }}</td>
            </tr>
            <tr>
                <td>Python</td>
                <td>{{ system_info.python_version }}</td>
            </tr>
            <tr>
                <td>Ollama</td>
                <td>{{ system_info.ollama_version }}</td>
            </tr>
            <tr>
                <td>evallm.py</td>
                <td>{{ system_info.evallm_version }}</td>
            </tr>
            <tr>
                <td>CPU</td>
                <td>{{ system_info.cpu.model }} ({{ system_info.cpu.cores }} cœurs, {{ system_info.cpu.threads }} threads)</td>
            </tr>
            <tr>
                <td>Mémoire</td>
                <td>{{ "%.1f"|format(system_info.memory.total_gb) }} GB total, {{ "%.1f"|format(system_info.memory.available_gb) }} GB disponible</td>
            </tr>
            {% if system_info.gpu %}
            <tr>
                <td>GPU</td>
                <td>
                    {% for gpu in system_info.gpu %}
                    {{ gpu.name }} ({{ "%.1f"|format(gpu.memory_total/1024) }} GB VRAM)<br>
                    {% endfor %}
                </td>
            </tr>
            {% endif %}
        </table>
    </div>
    
    <a href="{{ output_file|replace('.html', '.json') }}" class="json-link">📊 Voir les données au format JSON</a>

    <h2>Synthèse des Performances</h2>
    <table class="summary-table">
        <tr class="model-header">
            <th>Modèle</th>
            <th>Temps moyen (s)</th>
            <th>Temps minimum (s)</th>
            <th>Temps maximum (s)</th>
            <th>Nombre de tokens moyen</th>
        </tr>
        {% for model_temp, times in model_temp_times.items() %}
        <tr>
            <td><a href="#model_{{ model_temp_first_ids[model_temp] }}">{{ model_temp.split(' (')[0] }}</a> <span class="temp-badge">temp={{ model_temp.split('=')[1].split(')')[0] }}</span></td>
            <td>{{ "%.2f"|format(sum(times)/len(times)) }}</td>
            <td>{{ "%.2f"|format(min(times)) }}</td>
            <td>{{ "%.2f"|format(max(times)) }}</td>
            <td>{{ avg_tokens[model_temp] }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Données d'Entrée</h2>
    <div class="input-data">
        <h3>Prompts Système</h3>
        {% for id, prompt in unique_system_prompts.items() %}
        <p><strong>{{ id }}</strong></p>
        <div class="input-content">{{ prompt }}</div>
        {% endfor %}
        
        <h3>Prompts Utilisateur</h3>
        {% for id, prompt in unique_user_prompts.items() %}
        <p><strong>{{ id }}</strong></p>
        <div class="input-content">{{ prompt }}</div>
        {% endfor %}
        
        <h3>Contextes</h3>
        {% for id, context in unique_contexts.items() %}
        <p><strong>{{ id }}</strong></p>
        <div class="input-content">{{ context }}</div>
        {% endfor %}
    </div>
    
    <h2>Résultats Détaillés</h2>
    {% for (model, sys_id, prompt_id, ctx_id, temp), seeds in grouped_results.items() %}
    {% set model_temp_key = model ~ " (temp=" ~ temp ~ ")" %}
    <h3 id="model_{{ model_temp_first_ids[model_temp_key] }}">Modèle: {{ model }} | Système: {{ sys_id }} | Prompt: {{ prompt_id }} | Contexte: {{ ctx_id }} | Température: {{ temp }}</h3>
    <table class="results-table">
        <tr class="model-header">
            <th>Métrique</th>
            {% for seed in sorted_seeds %}
            <th>Réponse graine {{ seed }}</th>
            {% endfor %}
        </tr>
        <tr>
            <th>Temps (s)</th>
            {% for seed in sorted_seeds %}
            <td>{{ "%.2f"|format(seeds[seed].response_time) }}</td>
            {% endfor %}
        </tr>
        <tr>
            <th>Réponse</th>
            {% for seed in sorted_seeds %}
            <td class="response">
                {% if seeds[seed].response in previous_responses %}
                <div class="response-content identical">(identique)</div>
                {% else %}
                <div class="response-content response-text" onclick="showResponse({{ seeds[seed].response|tojson|replace('"', '&quot;')|replace('\n', '\\n')|replace('\r', '')|replace('\\', '\\\\')|safe }}, event)">
                    {{ seeds[seed].response|replace('<think>', '<span class="think-tag">&lt;think&gt;</span>')|replace('</think>', '<span class="think-tag">&lt;/think&gt;</span>')|safe }}
                </div>
                {% set _ = previous_responses.append(seeds[seed].response) %}
                {% endif %}
            </td>
            {% endfor %}
        </tr>
    </table>
    <br>
    {% endfor %}
    
    <h2>Modèles Disponibles</h2>
    <div class="models-list">
        {{ available_models|tojson }}
    </div>
    
    <div class="footer">
        <p>Généré avec <a href="https://github.com/Malapris/evallm">evallm.py</a> par Francis Malapris</p>
    </div>
</body>
</html>
"""

def get_system_info(ollama_url: str = DEFAULT_OLLAMA_URL) -> SystemInfo:
    """Récupère les informations système détaillées."""
    try:
        # Récupération des informations CPU
        cpu_freq = psutil.cpu_freq()
        cpu_info = {
            "model": platform.processor(),
            "cores": psutil.cpu_count(),
            "threads": psutil.cpu_count(logical=True),
            "freq": cpu_freq._asdict() if cpu_freq else None
        }
        
        # Récupération des informations mémoire
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": memory.total / GB_DIVISOR,
            "available_gb": memory.available / GB_DIVISOR,
            "used_gb": memory.used / GB_DIVISOR,
            "percent": memory.percent
        }
        
        # Récupération des informations GPU
        gpu_info = []
        try:
            gpus = GPUtil.getGPUs()
            gpu_info = [{
                "name": gpu.name,
                "memory_total": gpu.memoryTotal,
                "memory_used": gpu.memoryUsed,
                "memory_free": gpu.memoryFree,
                "gpu_load": gpu.load * 100
            } for gpu in gpus]
        except (ImportError, RuntimeError) as e:
            logger.warning(f"Impossible de récupérer les informations GPU: {e}")
        
        # Récupération de la version d'Ollama
        try:
            api_url = f"{ollama_url}/api/version"
            response = requests.get(api_url, timeout=5)
            ollama_version = response.json().get('version', 'Non disponible') if response.status_code == 200 else "Non disponible"
            if response.status_code != 200:
                logger.warning(f"Erreur lors de la récupération de la version d'Ollama: {response.status_code}")
        except Exception as e:
            logger.warning(f"Impossible de récupérer la version d'Ollama: {e}")
            ollama_version = "Non disponible"
        
        return SystemInfo(
            os=platform.system(),
            os_version=platform.version(),
            python_version=sys.version,
            ollama_version=ollama_version,
            evallm_version=EVALLM_VERSION,
            cpu=cpu_info,
            memory=memory_info,
            gpu=gpu_info,
            hostname=platform.node()
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations système: {e}")
        return None

def read_content_from_file_if_exists(content: str) -> str:
    """Lit le contenu d'un fichier s'il existe, sinon retourne la chaîne d'origine."""
    if isinstance(content, str) and Path(content).exists() and Path(content).is_file():
        try:
            logger.info(f"Lecture du contenu depuis le fichier: {content}")
            return Path(content).read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier {content}: {e}")
            return content
    return content

def warmup_model(model: str, system_prompt: str, user_prompt: str, context: str = "") -> None:
    """Préchauffage du modèle avec une graine 0."""
    logger.info(f"Préchauffage du modèle {model}...")
    full_prompt = f"{context}\n\n{user_prompt}" if context else user_prompt
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        for _ in range(1):
            ollama.chat(
                model=model,
                messages=messages,
                options={"seed": 0, "temperature": 0.0}
            )
            time.sleep(0.5)
        logger.info(f"Préchauffage réussi pour {model}")
    except Exception as e:
        logger.warning(f"Avertissement lors du préchauffage de {model}: {e}")

def compare_llms(config_file: str, output_file: Optional[str] = None, ollama_url: str = DEFAULT_OLLAMA_URL) -> List[Result]:
    """Compare différents LLM en utilisant Ollama selon la configuration spécifiée."""
    logger.info(f"Chargement de la configuration depuis {config_file}")
    logger.info(f"Utilisation du serveur Ollama: {ollama_url}")
    
    # Vérification du fichier de configuration
    config_path = Path(config_file)
    if not config_path.exists():
        logger.error(f"Le fichier de configuration {config_file} n'existe pas")
        return []
    
    try:
        # Chargement de la configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json_repair.load(f)
        config = ModelConfig(**config_data)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        return []
    
    # Validation de la configuration
    if not all([config.models, config.system_prompts, config.user_prompts]):
        logger.error("Configuration invalide: modèles, prompts système ou prompts utilisateur manquants")
        return []
    
    # Détermination du nom du fichier de sortie
    base_name = config_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{base_name}_{timestamp}.html"
    logger.info(f"Fichier de sortie : {output_file}")
    
    # Récupération des informations système
    system_info = get_system_info(ollama_url)
    
    # Initialisation du fichier JSON
    json_output = Path(output_file).with_suffix('.json')
    json_output.write_text(json.dumps({
        "system_info": system_info.__dict__,
        "config": config.model_dump(),
        "results": []
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    
    # Traitement des fichiers pour les prompts
    system_prompts = {k: read_content_from_file_if_exists(v) for k, v in config.system_prompts.items()}
    user_prompts = {k: read_content_from_file_if_exists(v) for k, v in config.user_prompts.items()}
    contexts = {k: read_content_from_file_if_exists(v) for k, v in config.contexts.items()}
    
    logger.info(f"Configuration chargée : {len(config.models)} modèles, {len(system_prompts)} prompts système, "
                f"{len(user_prompts)} prompts utilisateur, {len(contexts)} contextes")
    
    # Vérification des modèles disponibles
    try:
        # Configuration de l'URL d'Ollama
        ollama.base_url = ollama_url
        available_models = [model.model for model in ollama.list().models]
        for model in config.models:
            if model not in available_models:
                logger.warning(f"Le modèle '{model}' n'est pas disponible. Utilisez 'ollama pull {model}' pour le télécharger.")
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des modèles: {e}")
        logger.error("Assurez-vous qu'Ollama est installé et en cours d'exécution.")
        return []
    
    # Calcul du nombre total d'itérations
    total_iterations = len(config.models) * len(system_prompts) * len(user_prompts) * len(contexts) * len(config.seeds) * len(config.temperatures)
    logger.info(f"Nombre total d'itérations à effectuer : {total_iterations}")
    
    results = []
    current_model = None
    
    with Progress(*progress_columns, console=console) as progress:
        task = progress.add_task("Génération des réponses...", total=total_iterations)
        
        for model in config.models:
            if current_model != model:
                logger.info(f"Changement de modèle : passage à {model}")
                first_sys_prompt = next(iter(system_prompts.values()))
                first_user_prompt = next(iter(user_prompts.values()))
                first_context = next(iter(contexts.values()))
                warmup_model(model, first_sys_prompt, first_user_prompt, first_context)
                current_model = model
            
            for sys_id, system_prompt in system_prompts.items():
                for prompt_id, user_prompt in user_prompts.items():
                    for ctx_id, context in contexts.items():
                        for seed in config.seeds:
                            for temperature in config.temperatures:
                                logger.debug(f"Génération pour {model} (seed={seed}, temp={temperature})")
                                
                                full_prompt = f"{user_prompt}\n\n{context}" if context else user_prompt
                                start_time = time.time()
                                
                                try:
                                    response = ollama.chat(
                                        model=model,
                                        messages=[
                                            {"role": "system", "content": system_prompt},
                                            {"role": "user", "content": full_prompt}
                                        ],
                                        options={
                                            "seed": seed if seed is not None else None,
                                            "temperature": temperature
                                        }
                                    )
                                    
                                    result = Result(
                                        model=model,
                                        system_prompt=system_prompt,
                                        system_prompt_id=sys_id,
                                        user_prompt=user_prompt,
                                        user_prompt_id=prompt_id,
                                        context=context,
                                        context_id=ctx_id,
                                        seed=seed,
                                        temperature=temperature,
                                        response=response["message"]["content"],
                                        response_time=time.time() - start_time,
                                        commentaire=config.commentaire,
                                        Resultats=config.resultats if config.resultats else None
                                    )
                                    
                                except Exception as e:
                                    logger.error(f"Erreur avec {model} (temp={temperature}): {e}")
                                    result = Result(
                                        model=model,
                                        system_prompt=system_prompt,
                                        system_prompt_id=sys_id,
                                        user_prompt=user_prompt,
                                        user_prompt_id=prompt_id,
                                        context=context,
                                        context_id=ctx_id,
                                        seed=seed,
                                        temperature=temperature,
                                        response=f"ERREUR: {str(e)}",
                                        response_time=time.time() - start_time,
                                        commentaire=config.commentaire,
                                        Resultats=config.resultats if config.resultats else None
                                    )
                                
                                results.append(result)
                                
                                # Mise à jour du fichier JSON
                                try:
                                    json_data = json.loads(json_output.read_text(encoding='utf-8'))
                                    json_data["results"].append(result.model_dump())
                                    json_output.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
                                except Exception as e:
                                    logger.error(f"Erreur lors de l'écriture du résultat dans le fichier JSON: {e}")
                                
                                progress.update(task, advance=1)
    
    logger.info("Génération des réponses terminée")
    
    # Génération du rapport HTML avec Jinja2
    script_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(str(script_dir)))
    env.globals.update({
        'sum': sum,
        'len': len,
        'min': min,
        'max': max,
        'str': str,
        'float': float,
        'int': int,
        'round': round,
        'datetime': datetime
    })
    template = env.from_string(HTML_TEMPLATE)
    
    # Préparation des données pour le template
    model_temp_times = {}
    model_temp_first_ids = {}
    avg_tokens = {}
    unique_system_prompts = {}
    unique_user_prompts = {}
    unique_contexts = {}
    grouped_results = {}
    sorted_seeds = sorted(config.seeds)
    previous_responses = []
    
    # Organisation des résultats
    for result in results:
        model_temp_key = f"{result.model} (temp={result.temperature})"
        if model_temp_key not in model_temp_times:
            model_temp_times[model_temp_key] = []
            model_temp_first_ids[model_temp_key] = f"model_{result.model.replace(':', '_')}_{str(result.temperature).replace('.', '_')}"
            avg_tokens[model_temp_key] = 0
        
        model_temp_times[model_temp_key].append(result.response_time)
        
        # Collecte des prompts uniques
        unique_system_prompts[result.system_prompt_id] = result.system_prompt
        unique_user_prompts[result.user_prompt_id] = result.user_prompt
        unique_contexts[result.context_id] = result.context
        
        # Groupement des résultats
        group_key = (result.model, result.system_prompt_id, result.user_prompt_id, result.context_id, result.temperature)
        if group_key not in grouped_results:
            grouped_results[group_key] = {}
        grouped_results[group_key][result.seed] = result
    
    html_content = template.render(
        results=results,
        system_info=system_info,
        datetime=datetime,
        config=config,
        model_temp_times=model_temp_times,
        model_temp_first_ids=model_temp_first_ids,
        avg_tokens=avg_tokens,
        unique_system_prompts=unique_system_prompts,
        unique_user_prompts=unique_user_prompts,
        unique_contexts=unique_contexts,
        grouped_results=grouped_results,
        sorted_seeds=sorted_seeds,
        previous_responses=previous_responses,
        output_file=output_file,
        available_models=available_models
    )
    
    # Sauvegarde du rapport HTML
    Path(output_file).write_text(html_content, encoding='utf-8')
    logger.info(f"Rapport HTML sauvegardé dans {output_file}")
    
    # Ouverture du rapport dans le navigateur
    webbrowser.open('file://' + str(Path(output_file).absolute()))
    logger.info("Rapport ouvert dans le navigateur")
    
    # Sauvegarde des résultats dans un fichier JSON
    json_output = Path(output_file).with_suffix('.json')
    json_output.write_text(json.dumps({
        "system_info": system_info.__dict__,
        "config": config.model_dump(),
        "results": [result.model_dump() for result in results]
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    
    logger.info(f"Résultats sauvegardés dans {json_output}")
    
    return results

def main():
    """Fonction principale pour exécuter le script depuis la ligne de commande."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comparer des LLM avec Ollama et générer un rapport HTML")
    parser.add_argument("config", help="Fichier de configuration JSON", nargs='?')
    parser.add_argument("--output", "-o", help="Fichier de sortie HTML (optionnel)")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug")
    parser.add_argument("--list", action="store_true", help="Afficher la liste des modèles disponibles au format JSON")
    parser.add_argument("--ollama-url", help=f"URL du serveur Ollama (défaut: {DEFAULT_OLLAMA_URL})", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    if args.list:
        try:
            # Configuration de l'URL d'Ollama
            ollama.base_url = args.ollama_url
            available_models = [model.model for model in ollama.list().models]
            console.print_json(data=available_models)
            return
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles: {e}")
            return
    
    if not args.config:
        parser.error("Le fichier de configuration est requis sauf si --list est utilisé")
    
    compare_llms(args.config, args.output, args.ollama_url)

if __name__ == "__main__":
    main()
