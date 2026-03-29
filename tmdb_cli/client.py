import requests
from typing import Any, Dict, Optional

BASE_URL = "https://api.themoviedb.org/3/movie"

ENDPOINTS = {
    "playing": "now_playing",
    "popular": "popular",
    "top": "top_rated",
    "upcoming": "upcoming",
}


class TMDBClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        url = f"{BASE_URL}/{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Network/API error: {e}") from e

    def get_movies(self, category: str, page: int = 1) -> Dict[str, Any]:
        endpoint = ENDPOINTS[category]
        return self._get(endpoint, params={"page": page})
