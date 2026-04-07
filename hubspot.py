import requests
import os
import re
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.hubapi.com"
HEADERS = {
    "Authorization": f"Bearer {os.environ['HUBSPOT_API_KEY']}",
    "Content-Type": "application/json"
}
OWNER_IDS = ["75906518", "488757993"]
PIPELINE_ID = "290257090"
DEAL_STAGES = ["1409701055", "469976530", "470935799", "469976532"]
DISCOVERY_STAGE = "1409701055"

def get_open_deals():
    url = f"{BASE}/crm/v3/objects/deals/search"
    body = {
        "filterGroups": [{
            "filters": [
                {"propertyName": "hubspot_owner_id", "operator": "IN", "values": OWNER_IDS},
                {"propertyName": "pipeline", "operator": "EQ", "value": PIPELINE_ID},
                {"propertyName": "dealstage", "operator": "IN", "values": DEAL_STAGES}
            ]
        }],
        "properties": ["dealname", "amount", "closedate", "dealstage", "hubspot_owner_id"],
        "limit": 250
    }
    r = requests.post(url, headers=HEADERS, json=body)
    return r.json().get("results", [])

def get_deal_stage_history(deal_id):
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}?propertiesWithHistory=dealstage"
    r = requests.get(url, headers=HEADERS)
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
    r = requests.get(url, headers=HEADERS)
    call_ids = [c.get("id") for c in r.json().get("results", [])]
    latest_call = None
    latest_date = None
    for cid in call_ids:
        call_url = f"{BASE}/crm/v3/objects/calls/{cid}"
        params = {"properties": "hs_call_external_id,hs_createdate,hs_call_direction"}
        r2 = requests.get(call_url, headers=HEADERS, params=params)
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
    url = f"{BASE}/crm/v3/objects/deals/{deal_id}/associations/calls"
    r = requests.get(url, headers=HEADERS)
    call_ids = [c.get("id") for c in r.json().get("results", [])]
    latest_call = None
    latest_date = None
    for cid in call_ids:
        call_url = f"{BASE}/crm/v3/objects/calls/{cid}"
        params = {"properties": "hs_call_external_id,hs_createdate,hs_call_direction,hs_call_body"}
        r2 = requests.get(call_url, headers=HEADERS, params=params)
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
    r = requests.get(url, headers=HEADERS)
    results = r.json().get("results", [])
    if not results:
        return None
    company_id = results[0].get("id")
    company_url = f"{BASE}/crm/v3/objects/companies/{company_id}"
    params = {"properties": "name,industry,city,country,numberofemployees,annualrevenue"}
    r2 = requests.get(company_url, headers=HEADERS, params=params)
    return r2.json().get("properties", {})

def create_note(deal_id, body):
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
    r = requests.post(url, headers=HEADERS, json=data)
    return r.status_code == 201