import os
import json
import requests

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API_URL = os.environ["SPORTS_API_URL"]

STATE_FILE = "state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,"r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE,"w") as f:
        json.dump(state,f)


def send(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id":CHAT_ID,
            "text":msg,
            "parse_mode":"HTML"
        },
        timeout=20
    )


def get_matches():

    r = requests.get(API_URL,timeout=20)

    r.raise_for_status()

    return r.json()


def main():

    old = load_state()

    data = get_matches()

    new = {}

    for match in data["events"]:

        match_id = str(match["id"])

        status = match["status"]

        home = match["homeTeam"]["name"]

        away = match["awayTeam"]["name"]

        score = f'{match["homeScore"]}-{match["awayScore"]}'

        event = match.get("lastEvent","")

        value = {
            "status":status,
            "score":score,
            "event":event
        }

        if old.get(match_id) != value:

            text = (
                f"🏆 Mundial\n\n"
                f"<b>{home} vs {away}</b>\n\n"
                f"Marcador: {score}\n"
                f"Estado: {status}\n"
                f"Evento: {event}"
            )

            send(text)

        new[match_id]=value

    save_state(new)


if __name__=="__main__":
    main()
