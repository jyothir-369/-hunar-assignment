"""HTTP client for the Hunar Voice Agents API."""

from typing import Any, Optional

import httpx

from src.config import settings


class HunarAPIError(Exception):
    """Raised when the Hunar API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str, details: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Hunar API error {status_code}: {message}")


class HunarClient:
    """Thin wrapper around the Hunar Voice Agents REST API.

    Base URL: https://api.voice.hunar.ai/external/v1/
    Auth:     X-API-Key header
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.api_key: str = api_key or settings.HUNAR_API_KEY
        self.base_url: str = (base_url or settings.HUNAR_BASE_URL).rstrip("/")
        self._headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    # ─── Internals ───────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json,
            )
        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            raise HunarAPIError(
                status_code=response.status_code,
                message=str(payload),
                details=payload,
            )
        if not response.content:
            return None
        return response.json()

    # ─── AGENTS ──────────────────────────────────────────

    def list_agents(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._request(
            "GET", "agents/", params={"page": page, "page_size": page_size}
        )

    def create_agent(self, agent_data: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "agents/", json=agent_data)

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        return self._request("GET", f"agents/{agent_id}/")

    def update_agent(self, agent_id: str, agent_data: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"agents/{agent_id}/", json=agent_data)

    # ─── CALLS ───────────────────────────────────────────

    def create_call(
        self,
        agent_id: str,
        callee_name: str,
        mobile_number: str,
        custom_data: Optional[dict[str, Any]] = None,
        from_phone_number: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_config: Optional[dict[str, Any]] = None,
        guardrails: Optional[dict[str, Any]] = None,
        timezone: Optional[str] = None,
        callback_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        call_data: dict[str, Any] = {
            "agent_id": agent_id,
            "callee_name": callee_name,
            "mobile_number": mobile_number,
            "custom_data": custom_data or {},
        }
        if from_phone_number:
            call_data["from_phone_number"] = from_phone_number
        if request_id:
            call_data["request_id"] = request_id
        if retry_config:
            call_data["retry_config"] = retry_config
        if guardrails:
            call_data["guardrails"] = guardrails
        if timezone:
            call_data["timezone"] = timezone
        if callback_config:
            call_data["callback_config"] = callback_config

        return self._request("POST", "calls/", json=call_data)

    def create_bulk_calls(
        self,
        agent_id: str,
        data: list[dict[str, Any]],
        from_phone_number: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_config: Optional[dict[str, Any]] = None,
        guardrails: Optional[dict[str, Any]] = None,
        timezone: Optional[str] = None,
        callback_config: Optional[dict[str, Any]] = None,
        remove_invalid_rows: bool = True,
        remove_duplicate_phone_numbers: bool = True,
    ) -> Any:
        bulk_data: dict[str, Any] = {
            "agent_id": agent_id,
            "data": data,
            "remove_invalid_rows": remove_invalid_rows,
            "remove_duplicate_phone_numbers": remove_duplicate_phone_numbers,
        }
        if from_phone_number:
            bulk_data["from_phone_number"] = from_phone_number
        if request_id:
            bulk_data["request_id"] = request_id
        if retry_config:
            bulk_data["retry_config"] = retry_config
        if guardrails:
            bulk_data["guardrails"] = guardrails
        if timezone:
            bulk_data["timezone"] = timezone
        if callback_config:
            bulk_data["callback_config"] = callback_config

        return self._request("POST", "calls/bulk/", json=bulk_data)

    def get_call(self, call_id: str) -> dict[str, Any]:
        return self._request("GET", f"calls/{call_id}/")

    def list_calls(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[list[str]] = None,
        agent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = ",".join(status)
        if agent_id:
            params["agent_id"] = agent_id
        return self._request("GET", "calls/", params=params)

    # ─── NUMBERS ─────────────────────────────────────────

    def list_numbers(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        return self._request(
            "GET", "numbers/", params={"page": page, "page_size": page_size}
        )
