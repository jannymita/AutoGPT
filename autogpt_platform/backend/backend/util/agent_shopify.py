import requests

AGENT_SHOPIFY_ENDPOINT = os.getenv("AGENT_SHOPIFY_ENDPOINT")

def claim_store(owner_id: str):
    url = f"{AGENT_SHOPIFY_ENDPOINT}/store/owner"
    params = {'owner_id': owner_id}
    response = requests.put(url, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    return data

def get_store(store_handle: str):
    url = f"{AGENT_SHOPIFY_ENDPOINT}/store/{store_handle}"
    params = {'owner_id': owner_id}
    response = requests.get(url, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    return data