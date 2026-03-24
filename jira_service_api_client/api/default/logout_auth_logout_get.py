from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.logout_auth_logout_get_response_logout_auth_logout_get import LogoutAuthLogoutGetResponseLogoutAuthLogoutGet
from ...types import UNSET, Response


def _get_kwargs(
    *,
    user_id: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["user_id"] = user_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/auth/logout",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet | None:
    if response.status_code == 200:
        response_200 = LogoutAuthLogoutGetResponseLogoutAuthLogoutGet.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    user_id: str,
) -> Response[HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet]:
    """Logout

     Clear user session and log out.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet]

    """
    kwargs = _get_kwargs(
        user_id=user_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    user_id: str,
) -> HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet | None:
    """Logout

     Clear user session and log out.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet

    """
    return sync_detailed(
        client=client,
        user_id=user_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    user_id: str,
) -> Response[HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet]:
    """Logout

     Clear user session and log out.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet]

    """
    kwargs = _get_kwargs(
        user_id=user_id,
    )

    response = await client.get_async_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    user_id: str,
) -> HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet | None:
    """Logout

     Clear user session and log out.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LogoutAuthLogoutGetResponseLogoutAuthLogoutGet

    """
    return (
        await asyncio_detailed(
            client=client,
            user_id=user_id,
        )
    ).parsed
