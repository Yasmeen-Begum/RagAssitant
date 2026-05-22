import os, requests
from dotenv import load_dotenv

load_dotenv(override=True)
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def serper_search(query: str):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query}
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "link": item.get("link")
        })
    return results
