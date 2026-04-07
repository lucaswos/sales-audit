import os
from anthropic import Anthropic
from notion import get_rulebook
from prompt_cold_call import COLD_CALL_PROMPT
from hubspot import create_note
from analyze_discovery_prep import analyze_discovery_prep
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Anthropic()

def format_as_html(text):
    lines = text.split("\n")
    html = ""
    for line in lines:
        line = line.strip()
        if not line:
            html += "<br/>"
            continue
        elif line.startswith("## ") or line.startswith("# "):
            clean = line.replace("## ", "").replace("# ", "").replace("**", "")
            html += f"<h2>{clean}</h2><hr style='border:none;border-top:1px solid #ccc;margin:8px 0'/>"
        elif line.startswith("### "):
            clean = line.replace("### ", "").replace("**", "")
            html += f"<h3>{clean}</h3>"
        elif line.startswith("---"):
            html += "<hr style='border:none;border-top:1px solid #ccc;margin:12px 0'/>"
        elif line.startswith("| ") and "|" in line[1:]:
            if ":---" in line:
                continue
            cells = [c.strip().replace("**", "") for c in line.split("|") if c.strip()]
            if cells:
                row = "".join([f"<td style='padding:6px 8px;border:1px solid #ddd'>{c}</td>" for c in cells])
                html += f"<table style='width:100%;border-collapse:collapse'><tr>{row}</tr></table>"
        elif line.startswith("**") and line.endswith("**"):
            clean = line.replace("**", "")
            html += f"<p><strong>{clean}</strong></p>"
        elif line.startswith("- ") or line.startswith("* "):
            clean = line[2:].replace("**", "")
            html += f"<li>{clean}</li>"
        else:
            clean = line.replace("**", "")
            html += f"<p>{clean}</p>"
    return html

def analyze_cold_call(transcript, deal_id=None, sdr_name=None, company_name=None):
    try:
        rulebook = get_rulebook()

        prompt = COLD_CALL_PROMPT.format(
            notion_criteria=rulebook,
            transcript=transcript
        )

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        analysis = response.content[0].text

        if deal_id:
            today = datetime.now().strftime("%d.%m.%Y")
            sdr = sdr_name or "Unbekannter SDR"
            company = company_name or "Unbekannte Firma"

            title = f"🔍 SALES AUDIT – {company} | SDR: {sdr} | {today}"
            body_html = format_as_html(analysis)
            note_body = f"<h1>{title}</h1><hr/>{body_html}"
            create_note(deal_id, note_body)

            analyze_discovery_prep(
                sales_audit=analysis,
                deal_id=deal_id,
                company_name=company_name
            )

        return analysis
    except Exception as e:
        return f"Fehler bei der Analyse: {str(e)}"