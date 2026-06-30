import os
import json
import requests
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================

API_KEY = os.environ["FOOTBALL_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

STATE_FILE = "state.json"

WORLD_CUP_LEAGUE_ID = 1   # Cambiar si la API devuelve otro ID para el Mundial


# ==========================================
# ESTADO
# ==========================================

def load_state():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    return {
        "fixtures": {},
        "events": {}
    }


def save_state(state):

    with open(STATE_FILE, "w", encoding="utf-8") as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=4
        )


# ==========================================
# TELEGRAM
# ==========================================

def telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    r = requests.post(
        url,
        json=payload,
        timeout=30
    )

    return r.status_code == 200


# ==========================================
# API FOOTBALL
# ==========================================

def api(endpoint, params=None):

    url = BASE_URL + endpoint

    r = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    r.raise_for_status()

    return r.json()


# ==========================================
# PARTIDOS DEL MUNDIAL
# ==========================================

def fixtures_today():

    today = datetime.utcnow().strftime("%Y-%m-%d")

    data = api(

        "/fixtures",

        {

            "league": WORLD_CUP_LEAGUE_ID,

            "season": 2026,

            "date": today

        }

    )

    return data.get("response", [])


# ==========================================
# EVENTOS
# ==========================================

def fixture_events(fixture_id):

    data = api(

        "/fixtures/events",

        {

            "fixture": fixture_id

        }

    )

    return data.get("response", [])
    # ==========================================
# MENSAJES
# ==========================================

def status_text(short):

    mapping = {

        "NS": "⏳ No iniciado",

        "1H": "🟢 Comenzó el partido",

        "HT": "⏸️ Medio tiempo",

        "2H": "▶️ Comenzó el segundo tiempo",

        "ET": "⏱️ Tiempo extra",

        "BT": "⏸️ Descanso tiempo extra",

        "P": "🏆 Penales",

        "FT": "🏁 Final del partido",

        "AET": "🏁 Final tiempo extra",

        "PEN": "🏆 Final por penales",

        "INT": "Interrumpido",

        "SUSP": "Suspendido",

        "PST": "Pospuesto",

        "CANC": "Cancelado"

    }

    return mapping.get(short, short)


# ==========================================
# ESTADO DEL PARTIDO
# ==========================================

def check_fixture_status(fixture, state):

    fixture_id = str(fixture["fixture"]["id"])

    status = fixture["fixture"]["status"]["short"]

    elapsed = fixture["fixture"]["status"].get("elapsed")

    home = fixture["teams"]["home"]["name"]

    away = fixture["teams"]["away"]["name"]

    goals_home = fixture["goals"]["home"]

    goals_away = fixture["goals"]["away"]

    old = state["fixtures"].get(fixture_id)

    if old != status:

        message = (
            f"<b>{home}</b> vs <b>{away}</b>\n\n"
            f"{status_text(status)}\n\n"
            f"⚽ {goals_home}-{goals_away}"
        )

        if elapsed:

            message += f"\n⏱️ {elapsed}'"

        telegram(message)

        state["fixtures"][fixture_id] = status

    return fixture_id


# ==========================================
# EVENTOS
# ==========================================

def process_events(fixture_id, fixture, events, state):

    home = fixture["teams"]["home"]["name"]

    away = fixture["teams"]["away"]["name"]

    if fixture_id not in state["events"]:

        state["events"][fixture_id] = []

    known = state["events"][fixture_id]

    for event in events:

        minute = event["time"]["elapsed"]

        team = event["team"]["name"]

        player = event["player"]["name"]

        event_id = str(event.get("id", ""))

        if event_id in known:

            continue

        e_type = event["type"]

        detail = event["detail"]

        emoji = "ℹ️"

        text = detail

        if e_type == "Goal":

            emoji = "⚽"

            text = "GOOOOOOL"

        elif e_type == "Card":

            if "Red" in detail:

                emoji = "🟥"

            elif "Yellow" in detail:

                emoji = "🟨"

        elif e_type == "subst":

            emoji = "🔄"

        elif e_type == "Var":

            emoji = "📺"

        elif e_type == "Penalty":

            emoji = "🏆"

        message = (
            f"{emoji} <b>{home}</b> vs <b>{away}</b>\n\n"
            f"Equipo: <b>{team}</b>\n"
            f"Jugador: <b>{player}</b>\n"
            f"Evento: {text}\n"
            f"Minuto: {minute}'"
        )

        telegram(message)

        known.append(event_id)
        # ==========================================
# PROCESAR TODOS LOS PARTIDOS
# ==========================================

def process_matches():

    state = load_state()

    fixtures = fixtures_today()

    if len(fixtures) == 0:
        print("No hay partidos para hoy.")
        return

    print(f"Partidos encontrados: {len(fixtures)}")

    for fixture in fixtures:

        try:

            fixture_id = check_fixture_status(
                fixture,
                state
            )

            events = fixture_events(fixture_id)

            process_events(
                fixture_id,
                fixture,
                events,
                state
            )

        except Exception as e:

            print(
                f"Error procesando fixture {fixture_id}: {e}"
            )

    save_state(state)


# ==========================================
# MAIN
# ==========================================

def main():

    print("=" * 50)
    print("WORLD CUP TELEGRAM BOT")
    print("=" * 50)

    try:

        process_matches()

    except requests.exceptions.HTTPError as e:

        print("HTTP ERROR")
        print(e)

    except requests.exceptions.ConnectionError:

        print("Sin conexión.")

    except requests.exceptions.Timeout:

        print("Tiempo agotado.")

    except Exception as e:

        print("ERROR GENERAL")
        print(e)


# ==========================================
# EJECUCIÓN
# ==========================================

if __name__ == "__main__":

    main()
