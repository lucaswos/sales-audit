import os
import requests
import pathlib
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv(pathlib.Path(__file__).parent / ".env")

from aircall import get_transcription
from analyze_call import analyze_cold_call

PIPELINE_ID = "290257090"
DEAL_STAGES = ["1409701055", "469976530", "470935799", "469976532"]
DISCOVERY_STAGE = "1409701055"
BASE = "https://api.hubapi.com"

def get_headers():
    return {
        "Authorization": f"Bearer {os.environ['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }

def get_open_deals():
    url = f"{BASE}/crm/v3/objects/deals/search"
    all_results = []
    for owner_id in ["75906518", "488757993"]:
        for stage in DEAL_STAGES:
            body = {
                "filterGroups": [{
                    "filters": [
                        {"propertyName": "hubspot_owner_id", "operator": "EQ", "value": owner_id},
                        {"propertyName": "pipeline", "operator": "EQ", "value": PIPELINE_ID},
                        {"propertyName": "dealstage", "operator": "EQ", "value": stage}
                    ]
                }],
                "properties": ["dealname", "dealstage", "hubspot_owner_id"],
                "limit": 100
            }
            r = requests.post(url, headers=get_headers(), json=body)
            all_results.extend(r.json().get("results", []))
    return all_results

def get_deal_stage_history(deal_id):
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}?propertiesWithHistory=dealstage"
    r = requests.get(url, headers=get_headers())
    history = r.json().get("propertiesWithHistory", {}).get("dealstage", [])
    return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

def get_new_discovery_deals():
    deals = get_open_deals()
    new_deals = []
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for deal in deals:
        props = deal.get("properties", {})
        if props.get("dealstage") != DISCOVERY_STAGE:
            continue
        history = get_deal_stage_history(deal.get("id"))
        for entry in history:
            if entry.get("value") == DISCOVERY_STAGE:
                timestamp = entry.get("timestamp", "")
                if timestamp:
                    moved_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if moved_date >= today_start:
                        new_deals.append(deal)
                        break
    return new_deals

def get_aircall_id_from_deal(deal_id):
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}/associations/calls"
    r = requests.get(url, headers=get_headers())
    call_ids = [c.get("id") for c in r.json().get("results", [])]
    latest_call = None
    latest_date = None
    for cid in call_ids:
        call_url = f"{BASE}/crm/v3/objects/calls/{cid}"
        params = {"properties": "hs_call_external_id,hs_createdate,hs_call_direction"}
        r2 = requests.get(call_url, headers=get_headers(), params=params)
        props = r2.json().get("properties", {})
        direction = props.get("hs_call_direction", "")
        external_id = props.get("hs_call_external_id", "")
        created = props.get("hs_createdate", "")
        if direction == "OUTBOUND" and external_id and created:
            if latest_date is None or created > latest_date:
                latest_date = created
                latest_call = external_id
    return latest_call

def get_sdr_from_deal_call(deal_id):
    import re
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}/associations/calls"
    r = requests.get(url, headers=get_headers())
    call_ids = [c.get("id") for c in r.json().get("results", [])]
    latest_call = None
    latest_date = None
    for cid in call_ids:
        call_url = f"{BASE}/crm/v3/objects/calls/{cid}"
        params = {"properties": "hs_call_external_id,hs_createdate,hs_call_direction,hs_call_body"}
        r2 = requests.get(call_url, headers=get_headers(), params=params)
        props = r2.json().get("properties", {})
        direction = props.get("hs_call_direction", "")
        external_id = props.get("hs_call_external_id", "")
        created = props.get("hs_createdate", "")
        if direction == "OUTBOUND" and external_id and created:
            if latest_date is None or created > latest_date:
                latest_date = created
                latest_call = props
    if latest_call:
        body = latest_call.get("hs_call_body", "")
        match = re.search(r'made by <strong>([^<]+)</strong>', body)
        if match:
            return match.group(1)
    return "Unbekannter SDR"

def get_company_for_deal(deal_id):
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}/associations/companies"
    r = requests.get(url, headers=get_headers())
    results = r.json().get("results", [])
    if not results:
        return None
    company_id = results[0].get("id")
    company_url = f"{BASE}/crm/v3/objects/companies/{company_id}"
    params = {"properties": "name,industry,city,country,numberofemployees,annualrevenue"}
    r2 = requests.get(company_url, headers=get_headers(), params=params)
    return r2.json().get("properties", {})

def create_note(deal_id, body):
    import time
    url = f"{BASE}/crm/v3/objects/notes"
    data = {
        "properties": {
            "hs_note_body": body,
            "hs_timestamp": str(int(time.time() * 1000)),
        },
        "associations": [{
            "to": {"id": deal_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}]
        }]
    }
    r = requests.post(url, headers=get_headers(), json=data)
    return r.status_code == 201

def run():
    print("Pruefe neue Discovery Deals...")
    deals = get_new_discovery_deals()
    print(f"{len(deals)} neue Deals gefunden.")

    for deal in deals:
        props = deal.get("properties", {})
        deal_id = deal.get("id")
        deal_name = props.get("dealname", "Unbekannt")

        print(f"\nVerarbeite: {deal_name}")

        company = get_company_for_deal(deal_id)
        company_name = company.get("name", "") if company else deal_name

        aircall_id = get_aircall_id_from_deal(deal_id)
        if not aircall_id:
            print(f"Kein Aircall Call gefunden fuer {deal_name}")
            continue

        print(f"Aircall ID: {aircall_id}")

        transcript = get_transcription(aircall_id)
        if not transcript:
            print(f"Kein Transkript verfuegbar fuer {deal_name}")
            continue

        sdr = get_sdr_from_deal_call(deal_id)
        print(f"SDR: {sdr}")
        print(f"Analysiere Call...")

        result = analyze_cold_call(
            transcript,
            deal_id=deal_id,
            sdr_name=sdr,
            company_name=company_name
        )

        print(f"Analyse abgeschlossen fuer {deal_name}")

if __name__ == "__main__":
    run()