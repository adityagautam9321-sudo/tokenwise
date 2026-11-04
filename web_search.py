import os
import requests

def search_web(query: str) -> str:
    key = os.getenv("SERPAPI_KEY")
    if not key or not query:
        return ""
    try:
        res = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": key, "engine": "google"},
            timeout=12,
        ).json()
        results = res.get("organic_results", [])[:3]
        return "\n".join(
            f"- [{r.get('title')}]({r.get('link')}): {r.get('snippet')}" for r in results
        )
    except Exception:
        return ""