import os
from anthropic import Anthropic
from prompt_discovery_prep import DISCOVERY_PREP_PROMPT
from hubspot import create_note
from dotenv import load_dotenv
from datetime import datetime
import re

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
            clean = re.sub(r'\*+', '', line.replace("## ", "").replace("# ", ""))
            html += f"<h2>{clean}</h2><hr style='border:none;border-top:1px solid #ccc;margin:8px 0'/>"
        elif line.startswith("### "):
            clean = re.sub(r'\*+', '', line.replace("### ", ""))
            html += f"<h3>{clean}</h3>"
        elif line.startswith("---"):
            html += "<hr style='border:none;border-top:1px solid #ccc;margin:12px 0'/>"
        elif line.startswith("→"):
            clean = re.sub(r'\*+([^*]+)\*+', r'<strong>\1</strong>', line[1:].strip())
            html += f"<p style='color:#555;padding-left:16px'>{clean}</p>"
        elif re.match(r'^\*Warum kritisch:', line) or re.match(r'^\*Warum kritisch:', line):
            clean = re.sub(r'\*+', '', line)
            html += f"<p><em>{clean}</em></p>"
        elif line.startswith("[") and "]:" in line:
            parts = line.split("]:", 1)
            ziel = parts[0].replace("[", "")
            frage = parts[1].strip() if len(parts) > 1 else ""
            frage_clean = re.sub(r'\*+([^*]+)\*+', r'<strong>\1</strong>', frage)
            html += f"<p><strong>[{ziel}]:</strong> {frage_clean}</p>"
        elif line.startswith("- ") or line.startswith("* "):
            clean = re.sub(r'\*+([^*]+)\*+', r'<strong>\1</strong>', line[2:])
            html += f"<li>{clean}</li>"
        elif re.match(r'^\*\*.*\*\*$', line):
            clean = re.sub(r'\*+', '', line)
            html += f"<p><strong>{clean}</strong></p>"
        else:
            clean = re.sub(r'\*+([^*]+)\*+', r'<strong>\1</strong>', line)
            html += f"<p>{clean}</p>"
    return html

def analyze_discovery_prep(sales_audit, deal_id=None, company_name=None):
    try:
        prompt = DISCOVERY_PREP_PROMPT.format(
            sales_audit=sales_audit
        )

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        prep = response.content[0].text

        if deal_id:
            today = datetime.now().strftime("%d.%m.%Y")
            company = company_name or "Unbekannte Firma"
            title = f"📋 DISCOVERY-VORBEREITUNG – {company} | {today}"
            body_html = format_as_html(prep)
            note_body = f"<h1>{title}</h1><hr/>{body_html}"
            create_note(deal_id, note_body)

        return prep
    except Exception as e:
        return f"Fehler bei der Discovery-Vorbereitung: {str(e)}"
