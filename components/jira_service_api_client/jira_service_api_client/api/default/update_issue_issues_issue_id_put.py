from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.update_issue_issues_issue_id_put_response_update_issue_issues_issue_id_put import (
    UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut,
)
from ...models.update_issue_request import UpdateIssueRequest
from ...types import Response


def _get_kwargs(
    issue_id: str,
    *,
    body: UpdateIssueRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/issues/{issue_id}".format(
            issue_id=quote(str(issue_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut | None:
    if response.status_code == 200:
        response_200 = UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut.from_dict(response.json())

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
) -> Response[HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut]:
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
    body: UpdateIssueRequest,
) -> Response[HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut]:
    """Update Issue

     Update an existing issue.

    Only the fields present in the JSON body are updated; omitted fields are
    left unchanged.

    Args:
        issue_id: Jira issue key.
        body: Fields to update.
        client: Jira client instance (injected).

    Returns:
        Updated issue data.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 422: On invalid update data.
        HTTPException 500: On unexpected errors.

    Args:
        issue_id (str):
        body (UpdateIssueRequest): Request body for updating an existing issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    issue_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateIssueRequest,
) -> HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut | None:
    """Update Issue

     Update an existing issue.

    Only the fields present in the JSON body are updated; omitted fields are
    left unchanged.

    Args:
        issue_id: Jira issue key.
        body: Fields to update.
        client: Jira client instance (injected).

    Returns:
        Updated issue data.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 422: On invalid update data.
        HTTPException 500: On unexpected errors.

    Args:
        issue_id (str):
        body (UpdateIssueRequest): Request body for updating an existing issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut
    """

    return sync_detailed(
        issue_id=issue_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    issue_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateIssueRequest,
) -> Response[HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut]:
    """Update Issue

     Update an existing issue.

    Only the fields present in the JSON body are updated; omitted fields are
    left unchanged.

    Args:
        issue_id: Jira issue key.
        body: Fields to update.
        client: Jira client instance (injected).

    Returns:
        Updated issue data.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 422: On invalid update data.
        HTTPException 500: On unexpected errors.

    Args:
        issue_id (str):
        body (UpdateIssueRequest): Request body for updating an existing issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut]
    """

    kwargs = _get_kwargs(
        issue_id=issue_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    issue_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateIssueRequest,
) -> HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut | None:
    """Update Issue

     Update an existing issue.

    Only the fields present in the JSON body are updated; omitted fields are
    left unchanged.

    Args:
        issue_id: Jira issue key.
        body: Fields to update.
        client: Jira client instance (injected).

    Returns:
        Updated issue data.

    Raises:
        HTTPException 404: If the issue does not exist.
        HTTPException 422: On invalid update data.
        HTTPException 500: On unexpected errors.

    Args:
        issue_id (str):
        body (UpdateIssueRequest): Request body for updating an existing issue.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UpdateIssueIssuesIssueIdPutResponseUpdateIssueIssuesIssueIdPut
    """

    return (
        await asyncio_detailed(
            issue_id=issue_id,
            client=client,
            body=body,
        )
    ).parsed
