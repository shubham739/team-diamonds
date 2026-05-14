from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_issue_issues_post_response_create_issue_issues_post import (
    CreateIssueIssuesPostResponseCreateIssueIssuesPost,
)
from ...models.create_issue_request import CreateIssueRequest
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    *,
    body: CreateIssueRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/issues",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    if response.status_code == 201:
        response_201 = CreateIssueIssuesPostResponseCreateIssueIssuesPost.from_dict(response.json())

        return response_201

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateIssueRequest,
) -> Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]:
    """Create Issue

     Create a new issue.

    The request body (JSON) maps to the fields of a new Jira issue.

    Args:
        body: Issue fields (title, desc, status, members, due_date, board_id).
        client: Jira client instance (injected).

    Returns:
        Created issue data with HTTP 201.

    Raises:
        HTTPException 422: On invalid issue data.
        HTTPException 500: On unexpected errors.

    Args:
        body (CreateIssueRequest): Request body for creating a new issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: CreateIssueRequest,
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    """Create Issue

     Create a new issue.

    The request body (JSON) maps to the fields of a new Jira issue.

    Args:
        body: Issue fields (title, desc, status, members, due_date, board_id).
        client: Jira client instance (injected).

    Returns:
        Created issue data with HTTP 201.

    Raises:
        HTTPException 422: On invalid issue data.
        HTTPException 500: On unexpected errors.

    Args:
        body (CreateIssueRequest): Request body for creating a new issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateIssueRequest,
) -> Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]:
    """Create Issue

     Create a new issue.

    The request body (JSON) maps to the fields of a new Jira issue.

    Args:
        body: Issue fields (title, desc, status, members, due_date, board_id).
        client: Jira client instance (injected).

    Returns:
        Created issue data with HTTP 201.

    Raises:
        HTTPException 422: On invalid issue data.
        HTTPException 500: On unexpected errors.

    Args:
        body (CreateIssueRequest): Request body for creating a new issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateIssueRequest,
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    """Create Issue

     Create a new issue.

    The request body (JSON) maps to the fields of a new Jira issue.

    Args:
        body: Issue fields (title, desc, status, members, due_date, board_id).
        client: Jira client instance (injected).

    Returns:
        Created issue data with HTTP 201.

    Raises:
        HTTPException 422: On invalid issue data.
        HTTPException 500: On unexpected errors.

    Args:
        body (CreateIssueRequest): Request body for creating a new issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
