from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_issue_issues_issue_id_get_response_get_issue_issues_issue_id_get import (
    GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    issue_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/issues/{issue_id}".format(issue_id=quote(str(issue_id), safe="")),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError]:
    """Get Issue

     Get a single issue by ID.

    Args:
        issue_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        issue_id=issue_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    issue_id: str,
    *,
    client: AuthenticatedClient,
) -> GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError | None:
    """Get Issue

     Get a single issue by ID.

    Args:
        issue_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError

    """
    return sync_detailed(
        issue_id=issue_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError]:
    """Get Issue

     Get a single issue by ID.

    Args:
        issue_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        issue_id=issue_id,
    )

    response = await client.get_async_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio(
    issue_id: str,
    *,
    client: AuthenticatedClient,
) -> GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError | None:
    """Get Issue

     Get a single issue by ID.

    Args:
        issue_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        GetIssueIssuesIssueIdGetResponseGetIssueIssuesIssueIdGet | HTTPValidationError

    """
    return (
        await asyncio_detailed(
            issue_id=issue_id,
            client=client,
        )
    ).parsed
