# Estante Musical

**Estante Musical** es una línea editorial de Punto Común que convierte playlists en piezas curatoriales. Cada ficha lee una secuencia de canciones como un objeto narrativo: propone una tesis, describe su arco y comenta el lugar que ocupa cada canción.

> Spotify guarda las canciones; Estante Musical les devuelve portada, memoria y sentido.

## Piloto

[¿Algo contigo? — Así suena estar enamorado](fichas/algo-contigo.md) es la primera muestra del proyecto. La ficha presenta una lectura curatorial de una playlist y sirve como piloto del formato; su checklist editorial señala lo que falta para una publicación externa.

## Qué contiene este repositorio

- `fichas/`: piezas curatoriales piloto.
- `docs/criterios-editoriales.md`: guía de tono, privacidad y publicación.
- `examples/`: ejemplo de consulta del catálogo público de Spotify.
- `plantillas/ficha-playlist.md`: estructura reutilizable para nuevas fichas.

## Ejemplo de Spotify Web API

El ejemplo de `examples/spotify_catalog_search.py` muestra el flujo Client Credentials y busca canciones en el catálogo público. Solo imprime título, artistas y enlace de Spotify; no accede a cuentas, playlists privadas ni historial de escucha, y no guarda respuestas en disco.

1. Crea una app Web API en el [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Define `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET` en el entorno local. No los pegues en el código ni los subas al repositorio.
3. Ejecuta con Python 3.9 o posterior:

```powershell
$env:SPOTIFY_CLIENT_ID = "tu-client-id"
$env:SPOTIFY_CLIENT_SECRET = "tu-client-secret"
python examples/spotify_catalog_search.py "Algo contigo"
```

El mercado predeterminado es `MX`; puedes cambiarlo con `--market ES`. Este ejemplo consulta metadatos del catálogo: no mide reproducciones ni actividad de escucha.

## Principio de cuidado

Publicamos la pieza, no la traza de la persona. El historial de escucha y las notas privadas se quedan fuera de este repositorio. Una ficha debe sostenerse por su tesis, su secuencia y su lectura musical, sin revelar la identidad ni la biografía de terceras personas.

La presencia de una ficha aquí no implica que la playlist ya esté disponible públicamente en una plataforma. Los enlaces y materiales de publicación se agregan cuando estén confirmados.

## Derechos

El contenido editorial original de este repositorio está reservado a su autor. No se concede una licencia de reutilización. Los nombres de canciones, artistas y otros materiales de terceros pertenecen a sus respectivos titulares.
