from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.list_issues_issues_get_response_list_issues_issues_get import (
    ListIssuesIssuesGetResponseListIssuesIssuesGet,
)
from ...models.status import Status
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    title: None | str | Unset = UNSET,
    desc: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    members: list[str] | None | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
    max_results: int | Unset = 20,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_title: None | str | Unset
    if isinstance(title, Unset):
        json_title = UNSET
    else:
        json_title = title
    params["title"] = json_title

    json_desc: None | str | Unset
    if isinstance(desc, Unset):
        json_desc = UNSET
    else:
        json_desc = desc
    params["desc"] = json_desc

    json_status: None | str | Unset
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, Status):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_members: list[str] | None | Unset
    if isinstance(members, Unset):
        json_members = UNSET
    elif isinstance(members, list):
        json_members = members

    else:
        json_members = members
    params["members"] = json_members

    json_due_date: None | str | Unset
    if isinstance(due_date, Unset):
        json_due_date = UNSET
    else:
        json_due_date = due_date
    params["due_date"] = json_due_date

    params["max_results"] = max_results

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/issues",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet | None:
    if response.status_code == 200:
        response_200 = ListIssuesIssuesGetResponseListIssuesIssuesGet.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    desc: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    members: list[str] | None | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
    max_results: int | Unset = 20,
) -> Response[HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet]:
    """List Issues

     List issues with optional filters.

    Args:
        client: Jira client instance (injected).
        title: Filter by title substring.
        desc: Filter by description substring.
        status: Filter by status.
        members: Filter by member email.
        due_date: Filter by due date (YYYY-MM-DD).
        max_results: Maximum number of results to return (1–100).

    Returns:
        Dictionary with ``issues`` list and ``count``.

    Raises:
        HTTPException 422: On invalid query parameters.
        HTTPException 500: On unexpected errors.

    Args:
        title (None | str | Unset):
        desc (None | str | Unset):
        status (None | Status | Unset):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
        max_results (int | Unset):  Default: 20.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet]
    """

    kwargs = _get_kwargs(
        title=title,
        desc=desc,
        status=status,
        members=members,
        due_date=due_date,
        max_results=max_results,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    desc: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    members: list[str] | None | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
    max_results: int | Unset = 20,
) -> HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet | None:
    """List Issues

     List issues with optional filters.

    Args:
        client: Jira client instance (injected).
        title: Filter by title substring.
        desc: Filter by description substring.
        status: Filter by status.
        members: Filter by member email.
        due_date: Filter by due date (YYYY-MM-DD).
        max_results: Maximum number of results to return (1–100).

    Returns:
        Dictionary with ``issues`` list and ``count``.

    Raises:
        HTTPException 422: On invalid query parameters.
        HTTPException 500: On unexpected errors.

    Args:
        title (None | str | Unset):
        desc (None | str | Unset):
        status (None | Status | Unset):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
        max_results (int | Unset):  Default: 20.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet
    """

    return sync_detailed(
        client=client,
        title=title,
        desc=desc,
        status=status,
        members=members,
        due_date=due_date,
        max_results=max_results,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    desc: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    members: list[str] | None | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
    max_results: int | Unset = 20,
) -> Response[HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet]:
    """List Issues

     List issues with optional filters.

    Args:
        client: Jira client instance (injected).
        title: Filter by title substring.
        desc: Filter by description substring.
        status: Filter by status.
        members: Filter by member email.
        due_date: Filter by due date (YYYY-MM-DD).
        max_results: Maximum number of results to return (1–100).

    Returns:
        Dictionary with ``issues`` list and ``count``.

    Raises:
        HTTPException 422: On invalid query parameters.
        HTTPException 500: On unexpected errors.

    Args:
        title (None | str | Unset):
        desc (None | str | Unset):
        status (None | Status | Unset):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
        max_results (int | Unset):  Default: 20.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet]
    """

    kwargs = _get_kwargs(
        title=title,
        desc=desc,
        status=status,
        members=members,
        due_date=due_date,
        max_results=max_results,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    desc: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    members: list[str] | None | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
    max_results: int | Unset = 20,
) -> HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet | None:
    """List Issues

     List issues with optional filters.

    Args:
        client: Jira client instance (injected).
        title: Filter by title substring.
        desc: Filter by description substring.
        status: Filter by status.
        members: Filter by member email.
        due_date: Filter by due date (YYYY-MM-DD).
        max_results: Maximum number of results to return (1–100).

    Returns:
        Dictionary with ``issues`` list and ``count``.

    Raises:
        HTTPException 422: On invalid query parameters.
        HTTPException 500: On unexpected errors.

    Args:
        title (None | str | Unset):
        desc (None | str | Unset):
        status (None | Status | Unset):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
        max_results (int | Unset):  Default: 20.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListIssuesIssuesGetResponseListIssuesIssuesGet
    """

    return (
        await asyncio_detailed(
            client=client,
            title=title,
            desc=desc,
            status=status,
            members=members,
            due_date=due_date,
            max_results=max_results,
        )
    ).parsed
