"""Safe fetching for the URL mode (section 12).

The only place where the app requests something a stranger chose, so the only place where a
mistake reaches infrastructure nobody offered: the cloud metadata endpoint, a router, a
service on localhost.

The rules, and why each one exists:

- only ``http`` and ``https``: ``file:`` reads the disk and ``data:`` smuggles content;
- no credentials in the URL: they end up in logs and in the redirect chain;
- every hop resolves to public addresses only, and **all** addresses of a host must be
  public, so a mixed record cannot launder a private one;
- redirects are followed by hand, re-validating each target: delegating them to the HTTP
  client is the classic way an SSRF filter gets bypassed;
- a byte ceiling and a timeout, because an attacker controls the response.

Readability extraction is trafilatura's job; this module only decides what is allowed to be
read.
"""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit

import httpx

ALLOWED_SCHEMES = frozenset({"http", "https"})
TEXT_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 8.0
USER_AGENT = "FichaTecnica/0.2 (+lector de encuestas; contacto: repositorio)"


class FetchError(Exception):
    """The page could not be read, for a reason the caller may show to the user."""


class BlockedUrlError(FetchError):
    """The URL points somewhere the app refuses to go."""


class FetchTooLargeError(FetchError):
    """The response is larger than the ceiling the app accepts."""


Resolver = Callable[[str], list[str]]


def _system_resolver(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    return [str(info[4][0]) for info in infos]


def _is_public(address: str) -> bool:
    """True only for a globally routable address."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def _validate_target(url: str, resolve: Resolver) -> str:
    """Check scheme, credentials and every resolved address. Returns the host."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise BlockedUrlError(f"solo se permiten http y https, no {parts.scheme or 'sin esquema'}")
    if parts.username is not None or parts.password is not None:
        raise BlockedUrlError("la URL no puede llevar credenciales")
    host = parts.hostname
    if not host:
        raise BlockedUrlError("la URL no tiene host")

    try:
        literal = str(ipaddress.ip_address(host))
    except ValueError:
        try:
            addresses = resolve(host)
        except OSError as error:
            raise FetchError(f"no se pudo resolver {host}: {error}") from error
    else:
        addresses = [literal]

    if not addresses:
        raise FetchError(f"{host} no resuelve a ninguna direccion")
    if not all(_is_public(address) for address in addresses):
        raise BlockedUrlError(
            "la URL apunta a una red privada o local; por seguridad no se descarga"
        )
    return host


def _extract_text(body: bytes, content_type: str) -> str:
    """Readable text from the page. Falls back to the raw body when extraction finds nothing."""
    charset = "utf-8"
    for parameter in content_type.split(";")[1:]:
        name, _, value = parameter.strip().partition("=")
        if name.lower() == "charset" and value:
            charset = value.strip("\"'")
    try:
        html = body.decode(charset, errors="replace")
    except LookupError:
        html = body.decode("utf-8", errors="replace")

    if content_type.split(";")[0].strip().lower() == "text/plain":
        return html.strip()

    import trafilatura

    extracted = trafilatura.extract(html, favor_recall=True, include_comments=False)
    if extracted and extracted.strip():
        return extracted.strip()
    return (
        trafilatura.extract(html, favor_recall=True, include_comments=False, include_tables=False)
        or ""
    )


async def fetch_article(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    resolve: Resolver = _system_resolver,
    max_bytes: int = MAX_BYTES,
    max_redirects: int = MAX_REDIRECTS,
    timeout: float = TIMEOUT_SECONDS,
) -> str:
    """Download a page and return its readable text, or raise ``FetchError``."""
    owns_client = client is None
    http = client or httpx.AsyncClient()
    try:
        current = url
        for _ in range(max_redirects + 1):
            _validate_target(current, resolve)
            try:
                response = await http.get(
                    current,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain"},
                    timeout=timeout,
                    follow_redirects=False,
                )
            except httpx.TimeoutException as error:
                raise FetchError("la pagina tardo demasiado en responder") from error
            except httpx.HTTPError as error:
                raise FetchError(f"no se pudo descargar la pagina: {error}") from error

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise FetchError("redireccion sin destino")
                current = urljoin(current, location)
                continue

            if response.status_code >= 400:
                raise FetchError(f"la pagina respondio {response.status_code}")

            content_type = response.headers.get("content-type", "")
            if content_type.split(";")[0].strip().lower() not in TEXT_CONTENT_TYPES:
                raise FetchError("el enlace no es una pagina de texto; pega el texto de la noticia")

            body = response.content
            if len(body) > max_bytes:
                raise FetchTooLargeError(f"la pagina supera el maximo de {max_bytes // 1000} kB")
            text = _extract_text(body, content_type)
            if not text.strip():
                raise FetchError("no se pudo extraer texto de la pagina")
            return text

        raise FetchError(f"demasiadas redirecciones (maximo {max_redirects})")
    finally:
        if owns_client:
            await http.aclose()
