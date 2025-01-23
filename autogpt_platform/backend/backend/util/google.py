import os
import requests

GOOGLE_CUSTOM_SEARCH_API_KEY = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
GOOGLE_CUSTOM_SEARCH_CX = os.getenv("GOOGLE_CUSTOM_SEARCH_CX")
GOOGLE_CUSTOM_SEARCH_ENDPOINT = os.getenv("GOOGLE_CUSTOM_SEARCH_ENDPOINT", "https://www.googleapis.com/customsearch/v1")

def search_image(query: str) -> str:
  params = {
    "q": query,
    "key": GOOGLE_CUSTOM_SEARCH_API_KEY,
    "cx": GOOGLE_CUSTOM_SEARCH_CX,
    "searchType": "image",
    "num": 1  # Get only the first image
  }
  
  response = requests.get(GOOGLE_CUSTOM_SEARCH_ENDPOINT, params=params)
  if response.status_code == 200:
    results = response.json()
    if "items" in results and len(results["items"]) > 0 and "link" in results["items"][0]:
        return results["items"][0]["link"]
    
  return ""