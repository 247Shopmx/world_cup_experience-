import os
import json
import requests
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Headers necesarios para que ESPN no bloquee la petición
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

STATE_FILE = "state.json"
# Endpoint de ESPN para el Mundial (puede variar según el torneo, este es el standard)
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldcup/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldcup/summary"

# ==========================================
# ESTADO
# ==========================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"fixtures": {}, "events": {}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

# ==========================================
# TELEGRAM
# ==========================================

def telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=30)
        return r.status_code == 200
    except:
        return False

# ==========================================
# ESPN SCRAPING
# ==========================================

def get_matches():
    """Obtiene los partidos del día desde el scoreboard de ESPN"""
    r = requests.get(ESPN_SCOREBOARD_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("events", [])

def get_match_events(event_id):
    """Obtiene los eventos (goles, tarjetas) de un partido específico"""
    params = {"event": event_id}
    r = requests.get(ESPN_SUMMARY_URL, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    # Los eventos suelen estar en 'livePlays' o 'scoringPlays'
    return r.json().get("livePlays", [])

# ==========================================
# LÓGICA DE PROCESAMIENTO
# ==========================================

def process_matches():
    state = load_state()
    matches = get_matches()

    if not matches:
        print("No hay partidos programados.")
        return

    for match in matches:
        fixture_id = match["id"]
        status_code = match["status"]["type"]["state"] # "pre", "in", "post"
        
        # Mapeo de datos básicos
        home = match["competitions"][0]["competitors"][0]["team"]["displayName"]
        away = match["competitions"][0]["competitors"][0]["team"]["displayName"]
        # Nota: ESPN a veces invierte el orden, verificar índices de 'competitors'
        home = match["competitions"][0]["competitors"][0]["team"]["name"]
        away = match["competitions"][0]["competitors"][1]["team"]["name"]
        goals_home = match["competitions"][0]["competitors"][0]["score"]
        goals_away = match["competitions"][0]["competitors"][1]["score"]

        # 1. Procesar Estado
        old_status = state["fixtures"].get(fixture_id)
        if old_status != status_code:
            msg = f"<b>{home}</b> vs <b>{away}</b>\nEstado: {match['status']['type']['description']}\n⚽ {goals_home}-{goals_away}"
            telegram(msg)
            state["fixtures"][fixture_id] = status_code

        # 2. Procesar Eventos (solo si el partido está en juego)
        if status_code == "in":
            events = get_match_events(fixture_id)
            if fixture_id not in state["events"]:
                state["events"][fixture_id] = []
            
            for event in events:
                event_id = event["id"]
                if event_id not in state["events"][fixture_id]:
                    # Lógica simplificada de eventos
                    text = f"{event.get('clock', {}).get('displayValue', '')}' - {event.get('text', 'Evento')}"
                    telegram(f"📢 <b>{home} vs {away}</b>\n{text}")
                    state["events"][fixture_id].append(event_id)

    save_state(state)

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    try:
        process_matches()
    except Exception as e:
        print(f"Error crítico: {e}")
