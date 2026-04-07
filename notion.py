import requests
import os
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

RULEBOOK_PAGE_ID = "24d182495b0980f09602cd69bf653b50"

def get_block_text(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    r = requests.get(url, headers=HEADERS)
    blocks = r.json().get("results", [])
    text = ""
    for block in blocks:
        block_type = block.get("type")
        content = block.get(block_type, {})
        rich_text = content.get("rich_text", [])
        for rt in rich_text:
            text += rt.get("plain_text", "") + "\n"
        if block.get("has_children"):
            text += get_block_text(block["id"])
    return text

def get_rulebook():
    return get_block_text(RULEBOOK_PAGE_ID).strip()