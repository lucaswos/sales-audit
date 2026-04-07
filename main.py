import os
import requests
import pathlib
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

PIPELINE_ID = "290257090"
DEAL_STAGES = ["1409701055", "469976530", "470935799", "469976532"]

def get_headers():
    return {
        "Authorization": f"Bearer {os.environ['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }

def get_open_deals():
    url = "https://api.hubapi.com/crm/v3/objects/deals/search"
    all_results = []
    for owner_id in ["75906518", "488757993"]:
        body = {
            "filterGroups": [{
                "filters": [
                    {"propertyName": "hubspot_owner_id", "operator": "EQ", "value": owner_id},
                    {"propertyName": "pipeline", "operator": "EQ", "value": PIPELINE_ID},
                    {"propertyName": "dealstage", "operator": "IN", "values": DEAL_STAGES}
                ]
            }],
            "properties": ["dealname", "dealstage", "hubspot_owner_id"],
            "limit": 250
        }
        r = requests.post(url, headers=get_headers(), json=body)
        results = r.json().get("results", [])
        print(f"Owner {owner_id}: {len(results)} Deals, Status: {r.status_code}")
        all_results.extend(results)
    return all_results

def run():
    print("Pruefe neue Discovery Deals...")
    print(f"HUBSPOT_API_KEY vorhanden: {bool(os.environ.get('HUBSPOT_API_KEY'))}")
    deals = get_open_deals()
    print(f"Alle offenen Deals: {len(deals)}")

if __name__ == "__main__":
    run()