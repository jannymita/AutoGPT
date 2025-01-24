import os
import requests

GOOGLE_CUSTOM_SEARCH_API_KEY = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
GOOGLE_CUSTOM_SEARCH_CX = os.getenv("GOOGLE_CUSTOM_SEARCH_CX")
GOOGLE_CUSTOM_SEARCH_ENDPOINT = os.getenv("GOOGLE_CUSTOM_SEARCH_ENDPOINT", "https://www.googleapis.com/customsearch/v1")

def search_image_urls(query: str, count: int =1) -> list[str]:
  params = {
    "q": query,
    "key": GOOGLE_CUSTOM_SEARCH_API_KEY,
    "cx": GOOGLE_CUSTOM_SEARCH_CX,
    "searchType": "image",
    "num": count
  }
  
  response = requests.get(GOOGLE_CUSTOM_SEARCH_ENDPOINT, params=params)

  if response.status_code == 200:
    results = response.json()
    if isinstance(results.get("items", []), list):
      return [item["link"] for item in results["items"]]
  else:
    print("Error: ", " params: ", params, " status_code: ", response.status_code, response.text)

  return []