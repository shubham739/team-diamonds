"""OpenRouter API adapter with Jira tool definitions for LLM-powered chat."""

import os
from typing import Any, Self, cast

import requests
from fastapi import HTTPException
from llm_integration_api.interface.exceptions import LLMIntegrationError
from llm_integration_api.open_router_impl.open_router_client import OpenRouterClient as BaseOpenRouterClient

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"
_REQUEST_TIMEOUT_SECONDS = 60
_OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
JIRA_TOOL_TRIGGER = "@jira"

GENERAL_CHAT_SYSTEM_PROMPT = (
    "You are a helpful general-purpose assistant. Answer normal questions directly. "
    "Keep responses relatively short but informative by default, typically 2-5 sentences unless the user asks for more detail. "
    "When useful, use concise bullet points for clarity. "
    "Never ask the user questions, including clarifying or follow-up questions. "
    "Do not end responses with a question mark and do not request additional user input. "
    "Jira tools are only available when the user explicitly opts in with @jira. "
    "When @jira is present, help with Jira issues and boards using the provided tools when needed. "
    "When @jira is absent, do not attempt Jira-specific actions and answer conversationally instead. "
    "When calling Jira tools, always call them immediately using only the information the user provided. "
    "All tool parameters except those marked required are optional — omit them if not supplied. "
    "Never ask for missing optional parameters such as email, assignee, or due date. "
    "If the user says 'my issues' or 'my tasks' and no email is known, call list_issues with no members filter."
)

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


def jira_mode_requested(user_message: str) -> bool:
    """Return whether the user explicitly requested Jira-aware behavior."""
    return JIRA_TOOL_TRIGGER in user_message.lower()


def normalize_chat_message(user_message: str) -> str:
    """Remove the Jira trigger token before sending the user message to the model."""
    return user_message.replace(JIRA_TOOL_TRIGGER, "").strip() or user_message.strip()


class OpenRouterError(Exception):
    """Raised on OpenRouter API or network errors."""


class OpenRouterClient:
    """Compatibility adapter using llm-integration-api with tool-call support."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, site_url: str = "", app_name: str = "") -> None:
        """Initialise the client with API key/model and optional OpenRouter attribution headers."""
        resolved_api_key = (api_key or os.environ.get(_OPENROUTER_API_KEY_ENV, "")).strip()
        if not resolved_api_key:
            msg = "OpenRouter not configured: set OPENROUTER_API_KEY"
            raise OpenRouterError(msg)

        # Keep OPENROUTER_API_KEY available for downstream libraries that load credentials from env.
        os.environ[_OPENROUTER_API_KEY_ENV] = resolved_api_key

        try:
            self._client = BaseOpenRouterClient(api_key=resolved_api_key, model=model, site_url=site_url, app_name=app_name)
        except LLMIntegrationError as e:
            raise OpenRouterError(str(e)) from e
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {self._client.api_key}",
            "Content-Type": "application/json",
        }
        if site_url:
            self._headers["HTTP-Referer"] = site_url
        if app_name:
            self._headers["X-Title"] = app_name

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call OpenRouter /chat/completions and return the raw JSON response."""
        payload: dict[str, Any] = {"model": self._client.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            response = requests.post(
                BaseOpenRouterClient.BASE_URL,
                json=payload,
                headers=self._headers,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "unknown"
            body = e.response.text if e.response is not None else str(e)
            msg = f"OpenRouter API error {status_code}: {body}"
            raise OpenRouterError(msg) from e
        except requests.RequestException as e:
            msg = f"OpenRouter request failed: {e}"
            raise OpenRouterError(msg) from e
        parsed = response.json()
        if not isinstance(parsed, dict):
            msg = "OpenRouter returned an invalid response payload"
            raise OpenRouterError(msg)
        return cast("dict[str, Any]", parsed)

    def close(self) -> None:
        """Close resources used by the client."""
        # requests.post is stateless here; no persistent session to close.
        return

    def __enter__(self) -> Self:
        """Return self for use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close on context manager exit."""
        self.close()


def get_openrouter_client() -> OpenRouterClient:
    """FastAPI dependency — reads OPENROUTER_API_KEY and OPENROUTER_MODEL from environment."""
    api_key = os.environ.get(_OPENROUTER_API_KEY_ENV, "")
    if not api_key:
        raise HTTPException(status_code=503, detail=f"OpenRouter not configured: set {_OPENROUTER_API_KEY_ENV}")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    return OpenRouterClient(model=model)
