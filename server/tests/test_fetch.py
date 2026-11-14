"""ENC-13: fetching a URL without letting it become a weapon (section 12).

The URL mode is the only place where the app makes a request chosen by a stranger, so it is
also the only place where a mistake can reach infrastructure nobody asked to expose: the
cloud metadata endpoint at 169.254.169.254, a router at 192.168.1.1, a service on localhost.

Everything here is tested with an injected resolver and a fake transport: a test that
needed real DNS would pass or fail depending on the network, which is the opposite of what
a security test should do.
"""

import httpx
import pytest

from ficha_tecnica.api.fetch import (
    BlockedUrlError,
    FetchError,
    FetchTooLargeError,
    fetch_article,
)

PUBLIC_IP = "93.184.216.34"
HTML = "<html><body><p>SIMULACIÓN. Encuesta con 1.200 entrevistas.</p></body></html>"


def resolver_for(*addresses: str):
    def resolve(host: str) -> list[str]:
        return list(addresses)

    return resolve


def client_for(handler, follow_redirects: bool = False) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_a_public_url_is_fetched_and_read() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HTML)

    text = await fetch_article(
        "https://ejemplo.test/noticia",
        client=client_for(handler),
        resolve=resolver_for(PUBLIC_IP),
    )

    assert "1.200 entrevistas" in text


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "192.168.1.10",
        "172.16.0.1",
        "169.254.169.254",  # cloud metadata
        "0.0.0.0",
        "::1",
        "fd00::1",
    ],
)
async def test_private_and_local_targets_are_blocked(address: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must never be sent")

    with pytest.raises(BlockedUrlError):
        await fetch_article(
            "https://interno.test/noticia",
            client=client_for(handler),
            resolve=resolver_for(address),
        )


async def test_a_hostname_resolving_to_one_private_address_is_blocked() -> None:
    """A public A record must not launder a private one."""

    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must never be sent")

    with pytest.raises(BlockedUrlError):
        await fetch_article(
            "https://mixto.test/noticia",
            client=client_for(handler),
            resolve=resolver_for(PUBLIC_IP, "127.0.0.1"),
        )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://ejemplo.test/noticia",
        "gopher://ejemplo.test",
        "javascript:alert(1)",
        "data:text/html,<h1>hola</h1>",
    ],
)
async def test_only_http_and_https_are_allowed(url: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must never be sent")

    with pytest.raises(BlockedUrlError):
        await fetch_article(url, client=client_for(handler), resolve=resolver_for(PUBLIC_IP))


async def test_a_url_with_credentials_is_rejected() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must never be sent")

    with pytest.raises(BlockedUrlError):
        await fetch_article(
            "https://usuario:clave@ejemplo.test/noticia",
            client=client_for(handler),
            resolve=resolver_for(PUBLIC_IP),
        )


async def test_a_redirect_to_a_private_address_is_blocked() -> None:
    """Following a redirect without re-checking the target is how SSRF filters get bypassed."""
    redirected_to: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "publico.test":
            return httpx.Response(302, headers={"location": "http://interno.test/robo"})
        redirected_to.append(str(request.url))
        return httpx.Response(200, text=HTML)

    def resolve(host: str) -> list[str]:
        return ["127.0.0.1"] if host == "interno.test" else [PUBLIC_IP]

    with pytest.raises(BlockedUrlError):
        await fetch_article(
            "https://publico.test/noticia", client=client_for(handler), resolve=resolve
        )

    assert redirected_to == []


async def test_a_normal_redirect_is_followed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/viejo":
            return httpx.Response(301, headers={"location": "/nuevo"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HTML)

    text = await fetch_article(
        "https://ejemplo.test/viejo", client=client_for(handler), resolve=resolver_for(PUBLIC_IP)
    )

    assert "1.200 entrevistas" in text


async def test_too_many_redirects_is_an_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/otra"})

    with pytest.raises(FetchError):
        await fetch_article(
            "https://ejemplo.test/a", client=client_for(handler), resolve=resolver_for(PUBLIC_IP)
        )


async def test_an_oversized_body_is_rejected() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"a" * 3_000_000,
        )

    with pytest.raises(FetchTooLargeError):
        await fetch_article(
            "https://ejemplo.test/grande",
            client=client_for(handler),
            resolve=resolver_for(PUBLIC_IP),
        )


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "application/zip"])
async def test_a_non_text_response_is_rejected(content_type: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": content_type}, content=b"%PDF-1.4")

    with pytest.raises(FetchError):
        await fetch_article(
            "https://ejemplo.test/fichero",
            client=client_for(handler),
            resolve=resolver_for(PUBLIC_IP),
        )


async def test_a_timeout_is_reported_as_a_fetch_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("demasiado lento", request=request)

    with pytest.raises(FetchError):
        await fetch_article(
            "https://ejemplo.test/lento",
            client=client_for(handler),
            resolve=resolver_for(PUBLIC_IP),
        )


async def test_a_dns_failure_is_reported_as_a_fetch_error() -> None:
    def resolve(host: str) -> list[str]:
        raise OSError("no such host")

    async def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("the request must never be sent")

    with pytest.raises(FetchError):
        await fetch_article(
            "https://noexiste.test/noticia", client=client_for(handler), resolve=resolve
        )
