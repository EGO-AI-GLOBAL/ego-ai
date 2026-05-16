"""Cliente Supabase mínimo (PostgREST + Auth) sem storage/realtime.

Evita `supabase` meta-package → storage3 → pyiceberg → pyroaring (build C no Cloud).
API compatível com `create_client` / `.table()` / `.auth` usados em app.py.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from httpx import Client as SyncHttpxClient
from httpx import Timeout
from postgrest import SyncPostgrestClient, SyncRequestBuilder, SyncRPCFilterRequestBuilder
from postgrest.constants import DEFAULT_POSTGREST_CLIENT_TIMEOUT
from postgrest.types import CountMethod
from supabase_auth import (
    AuthFlowType,
    SyncGoTrueClient,
    SyncMemoryStorage,
    SyncSupportedStorage,
)
from supabase_auth.types import AuthChangeEvent, Session
from yarl import URL

DEFAULT_HEADERS = {"X-Client-Info": "ego-app/supabase-lite"}


class SupabaseException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class ClientOptions:
    schema: str = "public"
    headers: Dict[str, str] = field(default_factory=DEFAULT_HEADERS.copy)
    auto_refresh_token: bool = True
    persist_session: bool = True
    postgrest_client_timeout: Union[int, float, Timeout] = DEFAULT_POSTGREST_CLIENT_TIMEOUT
    flow_type: AuthFlowType = "pkce"
    storage: SyncSupportedStorage = field(default_factory=SyncMemoryStorage)
    httpx_client: Optional[SyncHttpxClient] = None


class SyncSupabaseAuthClient(SyncGoTrueClient):
    """Auth client — mesma assinatura que supabase._sync.auth_client."""

    def __init__(
        self,
        *,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        storage_key: Optional[str] = None,
        auto_refresh_token: bool = True,
        persist_session: bool = True,
        storage: Optional[SyncSupportedStorage] = None,
        http_client: Optional[SyncHttpxClient] = None,
        flow_type: AuthFlowType = "implicit",
        verify: bool = True,
        proxy: Optional[str] = None,
    ) -> None:
        if headers is None:
            headers = {}
        super().__init__(
            url=url,
            headers=headers,
            storage_key=storage_key,
            auto_refresh_token=auto_refresh_token,
            persist_session=persist_session,
            storage=storage,
            http_client=http_client,
            flow_type=flow_type,
            verify=verify,
            proxy=proxy,
        )


class Client:
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        options: Optional[ClientOptions] = None,
    ) -> None:
        if not supabase_url:
            raise SupabaseException("supabase_url is required")
        if not supabase_key:
            raise SupabaseException("supabase_key is required")
        if not re.match(r"^(https?)://.+", supabase_url):
            raise SupabaseException("Invalid URL")

        if options is None:
            options = ClientOptions(storage=SyncMemoryStorage())

        self.supabase_url = (
            URL(supabase_url) if supabase_url.endswith("/") else URL(supabase_url + "/")
        )
        self.supabase_key = supabase_key
        self.options = copy.copy(options)
        self.options.headers = {**options.headers, **self._get_auth_headers()}

        self.rest_url = self.supabase_url.joinpath("rest", "v1")
        self.auth_url = self.supabase_url.joinpath("auth", "v1")

        self.auth = self._init_supabase_auth_client(
            auth_url=str(self.auth_url),
            client_options=self.options,
        )
        self._postgrest: Optional[SyncPostgrestClient] = None
        self.auth.on_auth_state_change(self._listen_to_auth_events)

    @classmethod
    def create(
        cls,
        supabase_url: str,
        supabase_key: str,
        options: Optional[ClientOptions] = None,
    ) -> Client:
        auth_header = options.headers.get("Authorization") if options else None
        client = cls(supabase_url, supabase_key, options)

        if auth_header is None:
            try:
                session = client.auth.get_session()
                session_access_token = (
                    client._create_auth_header(session.access_token) if session else None
                )
            except Exception:
                session_access_token = None
            client.options.headers.update(client._get_auth_headers(session_access_token))

        return client

    def table(self, table_name: str) -> SyncRequestBuilder:
        return self.from_(table_name)

    def from_(self, table_name: str) -> SyncRequestBuilder:
        return self.postgrest.from_(table_name)

    def schema(self, schema: str) -> SyncPostgrestClient:
        return self.postgrest.schema(schema)

    def rpc(
        self,
        fn: str,
        params: Optional[Dict[Any, Any]] = None,
        count: Optional[CountMethod] = None,
        head: bool = False,
        get: bool = False,
    ) -> SyncRPCFilterRequestBuilder:
        if params is None:
            params = {}
        return self.postgrest.rpc(fn, params, count, head, get)

    @property
    def postgrest(self) -> SyncPostgrestClient:
        if self._postgrest is None:
            self._postgrest = self._init_postgrest_client(
                rest_url=str(self.rest_url),
                headers=self.options.headers,
                schema=self.options.schema,
                timeout=self.options.postgrest_client_timeout,
                http_client=self.options.httpx_client,
            )
        return self._postgrest

    @staticmethod
    def _init_supabase_auth_client(
        auth_url: str,
        client_options: ClientOptions,
        verify: bool = True,
        proxy: Optional[str] = None,
    ) -> SyncSupabaseAuthClient:
        return SyncSupabaseAuthClient(
            url=auth_url,
            auto_refresh_token=client_options.auto_refresh_token,
            persist_session=client_options.persist_session,
            storage=client_options.storage,
            headers=client_options.headers,
            flow_type=client_options.flow_type,
            verify=verify,
            proxy=proxy,
            http_client=client_options.httpx_client,
        )

    @staticmethod
    def _init_postgrest_client(
        rest_url: str,
        headers: Dict[str, str],
        schema: str,
        timeout: Union[int, float, Timeout] = DEFAULT_POSTGREST_CLIENT_TIMEOUT,
        verify: bool = True,
        proxy: Optional[str] = None,
        http_client: Optional[SyncHttpxClient] = None,
    ) -> SyncPostgrestClient:
        if http_client is not None:
            return SyncPostgrestClient(
                rest_url, headers=headers, schema=schema, http_client=http_client
            )
        return SyncPostgrestClient(
            rest_url,
            headers=headers,
            schema=schema,
            timeout=timeout,
            verify=verify,
            proxy=proxy,
            http_client=None,
        )

    def _create_auth_header(self, token: str) -> str:
        return f"Bearer {token}"

    def _get_auth_headers(self, authorization: Optional[str] = None) -> Dict[str, str]:
        if authorization is None:
            authorization = self.options.headers.get(
                "Authorization", self._create_auth_header(self.supabase_key)
            )
        return {
            "apiKey": self.supabase_key,
            "Authorization": authorization,
        }

    def _listen_to_auth_events(
        self, event: AuthChangeEvent, session: Optional[Session]
    ) -> None:
        access_token = self.supabase_key
        if event in ["SIGNED_IN", "TOKEN_REFRESHED", "SIGNED_OUT"]:
            self._postgrest = None
            access_token = session.access_token if session else self.supabase_key
        auth_header = self._create_auth_header(access_token)
        self.options.headers["Authorization"] = auth_header
        self.auth._headers["Authorization"] = auth_header


def create_client(
    supabase_url: str,
    supabase_key: str,
    options: Optional[ClientOptions] = None,
) -> Client:
    return Client.create(supabase_url=supabase_url, supabase_key=supabase_key, options=options)
