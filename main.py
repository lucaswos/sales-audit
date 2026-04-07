import os
import requests
import pathlib
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

PIPELINE_ID = "290257090"
DEAL_STAGES = ["1409701055", "469976530", "470935799", "469976532"]
DISCOVERY_STAGE = "1409701055"

def get_headers():
    return {
        "Authorization": f"Bearer {os.environ['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }

def get_open_deals():
    url = "https://api.hubapi.com/crm/v3/objects/deals/search"
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
            results = r.json().get("results", [])
            all_results.extend(results)
    return all_results

def get_deal_stage_history(deal_id):
    url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}?propertiesWithHistory=dealstage"
    r = requests.get(url, headers=get_headers())
    history = r.json().get("propertiesWithHistory", {}).get("dealstage", [])
    return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

def get_new_discovery_deals():
    from datetime import datetime, timezone
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

def run():
    print("Pruefe neue Discovery Deals...")
    print(f"HUBSPOT_API_KEY vorhanden: {bool(os.environ.get('HUBSPOT_API_KEY'))}")
    all_deals = get_open_deals()
    print(f"Alle offenen Deals: {len(all_deals)}")
    deals = get_new_discovery_deals()
    print(f"Neue Discovery Deals heute: {len(deals)}")
    for d in deals:
        print(f"  - {d.get('properties', {}).get('dealname')}")

if __name__ == "__main__":
    run()