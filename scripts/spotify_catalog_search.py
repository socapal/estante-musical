"""Search Spotify's public catalog without accessing user account data."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"


class SpotifyApiError(RuntimeError):
    """A short, safe-to-display error from the Spotify API request."""


def _read_json(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        raise SpotifyApiError(f"Spotify devolvió HTTP {error.code}.") from None
    except URLError:
        raise SpotifyApiError("No se pudo conectar con Spotify.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SpotifyApiError("Spotify devolvió una respuesta no válida.") from None

    if not isinstance(payload, dict):
        raise SpotifyApiError("Spotify devolvió una respuesta no válida.")
    return payload


def get_access_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("ascii")
    request = Request(
        TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode("ascii"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    payload = _read_json(request)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise SpotifyApiError("La respuesta de Spotify no incluyó un token válido.")
    return token


def search_tracks(
    access_token: str, query: str, market: str = "MX", limit: int = 5
) -> list[dict[str, str]]:
    params = urlencode(
        {"q": query, "type": "track", "market": market, "limit": limit}
    )
    request = Request(
        f"{SEARCH_URL}?{params}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    payload = _read_json(request)
    track_container = payload.get("tracks")
    if not isinstance(track_container, dict):
        raise SpotifyApiError("El formato de resultados de Spotify no es válido.")
    tracks = track_container.get("items", [])
    if not isinstance(tracks, list):
        raise SpotifyApiError("El formato de resultados de Spotify no es válido.")

    results = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        artists = track.get("artists", [])
        external_urls = track.get("external_urls", {})
        results.append(
            {
                "name": str(track.get("name", "Sin título")),
                "artists": ", ".join(
                    str(artist["name"])
                    for artist in artists
                    if isinstance(artist, dict) and isinstance(artist.get("name"), str)
                ),
                "url": str(external_urls.get("spotify", ""))
                if isinstance(external_urls, dict)
                else "",
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Busca canciones en el catálogo público de Spotify."
    )
    parser.add_argument("query", help="Texto para buscar en el catálogo")
    parser.add_argument("--market", default="MX", help="Código de mercado (default: MX)")
    args = parser.parse_args()

    query = args.query.strip()
    market = args.market.upper()
    if not query:
        parser.error("la búsqueda no puede estar vacía")
    if not re.fullmatch(r"[A-Z]{2}", market):
        parser.error("--market debe ser un código de país de dos letras, como MX")

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            "Configura SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en el entorno.",
            file=sys.stderr,
        )
        return 2

    try:
        token = get_access_token(client_id, client_secret)
        tracks = search_tracks(token, query, market)
    except SpotifyApiError as error:
        print(error, file=sys.stderr)
        return 1

    if not tracks:
        print("No se encontraron canciones.")
        return 0

    for track in tracks:
        print(f"{track['name']} — {track['artists']}\n{track['url']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
