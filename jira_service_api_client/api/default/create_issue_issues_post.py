from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_issue_issues_post_response_create_issue_issues_post import (
    CreateIssueIssuesPostResponseCreateIssueIssuesPost,
)
from ...models.http_validation_error import HTTPValidationError
from ...models.status import Status
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    title: None | str | Unset = UNSET,
    description: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_title: None | str | Unset
    if isinstance(title, Unset):
        json_title = UNSET
    else:
        json_title = title
    params["title"] = json_title

    json_description: None | str | Unset
    if isinstance(description, Unset):
        json_description = UNSET
    else:
        json_description = description
    params["description"] = json_description

    json_status: None | str | Unset
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, Status):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_assignee: None | str | Unset
    if isinstance(assignee, Unset):
        json_assignee = UNSET
    else:
        json_assignee = assignee
    params["assignee"] = json_assignee

    json_due_date: None | str | Unset
    if isinstance(due_date, Unset):
        json_due_date = UNSET
    else:
        json_due_date = due_date
    params["due_date"] = json_due_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/issues",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = CreateIssueIssuesPostResponseCreateIssueIssuesPost.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
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
    title: None | str | Unset = UNSET,
    description: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
) -> Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]:
    """Create Issue

     Create a new issue.

    Args:
        title (None | str | Unset):
        description (None | str | Unset):
        status (None | Status | Unset):
        assignee (None | str | Unset):
        due_date (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        title=title,
        description=description,
        status=status,
        assignee=assignee,
        due_date=due_date,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    description: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    """Create Issue

     Create a new issue.

    Args:
        title (None | str | Unset):
        description (None | str | Unset):
        status (None | Status | Unset):
        assignee (None | str | Unset):
        due_date (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError

    """
    return sync_detailed(
        client=client,
        title=title,
        description=description,
        status=status,
        assignee=assignee,
        due_date=due_date,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    description: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
) -> Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]:
    """Create Issue

     Create a new issue.

    Args:
        title (None | str | Unset):
        description (None | str | Unset):
        status (None | Status | Unset):
        assignee (None | str | Unset):
        due_date (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        title=title,
        description=description,
        status=status,
        assignee=assignee,
        due_date=due_date,
    )

    response = await client.get_async_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    title: None | str | Unset = UNSET,
    description: None | str | Unset = UNSET,
    status: None | Status | Unset = UNSET,
    assignee: None | str | Unset = UNSET,
    due_date: None | str | Unset = UNSET,
) -> CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError | None:
    """Create Issue

     Create a new issue.

    Args:
        title (None | str | Unset):
        description (None | str | Unset):
        status (None | Status | Unset):
        assignee (None | str | Unset):
        due_date (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateIssueIssuesPostResponseCreateIssueIssuesPost | HTTPValidationError

    """
    return (
        await asyncio_detailed(
            client=client,
            title=title,
            description=description,
            status=status,
            assignee=assignee,
            due_date=due_date,
        )
    ).parsed
