import os
import pathlib
import requests
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from hubspot import get_new_discovery_deals, get_open_deals, get_aircall_id_from_deal, get_sdr_from_deal_call, get_company_for_deal, get_headers
from aircall import get_transcription
from analyze_call import analyze_cold_call

def run():
    print("Pruefe neue Discovery Deals...")
    print(f"HUBSPOT_API_KEY vorhanden: {bool(os.environ.get('HUBSPOT_API_KEY'))}")

    r = requests.post(
        'https://api.hubapi.com/crm/v3/objects/deals/search',
        headers=get_headers(),
        json={
            "filterGroups": [{"filters": [{"propertyName": "hubspot_owner_id", "operator": "EQ", "value": "75906518"}]}],
            "properties": ["dealname"],
            "limit": 5
        }
    )
    print(f"API Status: {r.status_code}, Total: {r.json().get('total', 0)}, Error: {r.json().get('message', '')}")

    all_deals = get_open_deals()
    print(f"Alle offenen Deals: {len(all_deals)}")

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
        result = analyze_cold_call(transcript, deal_id=deal_id, sdr_name=sdr, company_name=company_name)
        print(f"Analyse abgeschlossen fuer {deal_name}")

if __name__ == "__main__":
    run()