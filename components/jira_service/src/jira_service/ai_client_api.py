"""OpenRouter API client with Jira tool definitions for LLM-powered chat."""

import os
from typing import Any, Self

import httpx
from fastapi import HTTPException

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"
_BASE_URL = "https://openrouter.ai/api/v1"

JIRA_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List Jira issues with optional filters. Use to search for issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Filter by title substring"},
                    "desc": {"type": "string", "description": "Filter by description substring"},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "complete", "cancelled"],
                    },
                    "members": {"type": "array", "items": {"type": "string"}, "description": "Filter by member emails"},
                    "due_date": {"type": "string", "description": "Filter by due date (YYYY-MM-DD)"},
                    "max_results": {"type": "integer", "description": "Max results (1-100, default 20)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Fetch a single Jira issue by its key (e.g. PROJ-42).",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string", "description": "Jira issue key"},
                },
                "required": ["issue_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_issue",
            "description": "Create a new Jira issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "desc": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "complete", "cancelled"],
                    },
                    "members": {"type": "array", "items": {"type": "string"}, "description": "Member emails"},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                    "board_id": {"type": "string", "description": "Board ID"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_issue",
            "description": "Update fields on an existing Jira issue. Only supplied fields are changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string", "description": "Jira issue key"},
                    "title": {"type": "string"},
                    "desc": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "complete", "cancelled"],
                    },
                    "members": {"type": "array", "items": {"type": "string"}},
                    "due_date": {"type": "string"},
                    "board_id": {"type": "string"},
                },
                "required": ["issue_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_issue",
            "description": "Permanently delete a Jira issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string", "description": "Jira issue key"},
                },
                "required": ["issue_id"],
            },
        },
    },
]


class OpenRouterError(Exception):
    """Raised on OpenRouter API or network errors."""


class OpenRouterClient:
    """Thin httpx wrapper for OpenRouter /chat/completions with tool use."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        """Initialise the client with an API key and optional model override."""
        self._model = model
        self._http = httpx.Client(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call /chat/completions and return the parsed JSON response."""
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            response = self._http.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"OpenRouter API error {e.response.status_code}: {e.response.text}"
            raise OpenRouterError(msg) from e
        except httpx.RequestError as e:
            msg = f"OpenRouter request failed: {e}"
            raise OpenRouterError(msg) from e
        return response.json()  # type: ignore[no-any-return]

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> Self:
        """Return self for use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close on context manager exit."""
        self.close()


def get_openrouter_client() -> OpenRouterClient:
    """FastAPI dependency — reads OPENROUTER_API_KEY and OPENROUTER_MODEL from environment."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenRouter not configured: set OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    return OpenRouterClient(api_key=api_key, model=model)
