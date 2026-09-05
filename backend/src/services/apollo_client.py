"""HTTP client for the Apollo.io people search / enrichment API."""

from typing import Any, Optional

import httpx


APOLLO_BASE_URL = "https://api.apollo.io/v1"


class ApolloClient:
    """Thin wrapper around the Apollo.io people search & enrichment API."""

    def __init__(self, api_key: str, base_url: str = APOLLO_BASE_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _request(self, method: str, path: str, *, json: dict[str, Any]) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, url, headers=self._headers, json=json)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def search_candidates(
        self,
        job_title: str,
        seniority_levels: list[str],
        locations: list[str],
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "q_keywords": job_title,
            "seniority": seniority_levels,
            "location": locations,
            "page": page,
            "per_page": per_page,
        }
        return self._request("POST", "mixed_people/api_search", json=payload)

    def enrich_person(
        self,
        email: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if email:
            payload["email"] = email
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        return self._request("POST", "people/match", json=payload)

    def parse_results(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize Apollo's people-search response into a list of candidate dicts."""
        candidates: list[dict[str, Any]] = []
        for person in data.get("people", []) or []:
            organization = person.get("organization") or {}
            candidates.append(
                {
                    "name": person.get("name", ""),
                    "title": person.get("title", ""),
                    "company": organization.get("name", ""),
                    "phone": person.get("phone_number", ""),
                    "email": person.get("email", ""),
                    "linkedin_url": person.get("linkedin_url", ""),
                    "city": person.get("city", ""),
                    "country": person.get("country", ""),
                    "seniority": person.get("seniority_level", ""),
                    "apollo_id": person.get("id", ""),
                }
            )
        return candidates
