import requests
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

AUTH = (os.environ['AIRCALL_API_ID'], os.environ['AIRCALL_API_TOKEN'])
BASE = "https://api.aircall.io/v1"

def get_transcription(call_id):
    r = requests.get(f"{BASE}/calls/{call_id}/transcription", auth=AUTH)
    if r.status_code == 200:
        data = r.json().get("transcription", {})
        utterances = data.get("content", {}).get("utterances", [])
        text = ""
        for u in utterances:
            speaker = "SDR" if u.get("participant_type") == "internal" else "Kunde"
            content = u.get("text", "")
            text += f"{speaker}: {content}\n"
        return text.strip()
    return None