from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"
MANIFEST_PATH = INTERIM_DIR / "ingest_manifest.json"
MUSIC_OUTPUT = INTERIM_DIR / "streaming_history_audio_raw.csv"
NON_MUSIC_OUTPUT = INTERIM_DIR / "streaming_history_non_music_raw.csv"

CANONICAL_FIELDS = [
    "source_file",
    "source_family",
    "content_type",
    "ts",
    "username",
    "platform",
    "ms_played",
    "conn_country",
    "ip_addr_decrypted",
    "user_agent_decrypted",
    "master_metadata_track_name",
    "master_metadata_album_artist_name",
    "master_metadata_album_album_name",
    "spotify_track_uri",
    "episode_name",
    "episode_show_name",
    "spotify_episode_uri",
    "reason_start",
    "reason_end",
    "shuffle",
    "skipped",
    "offline",
    "offline_timestamp",
    "incognito_mode",
]


def history_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []

    matches: list[Path] = []
    for path in RAW_DIR.rglob("*.json"):
        lower_name = path.name.lower()
        if "streaminghistory" in lower_name or "streaming_history" in lower_name or "endsong" in lower_name:
            matches.append(path)
    return sorted(matches)


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return [item for item in value if isinstance(item, dict)]

    return []


def source_family(path: Path) -> str:
    lower_name = path.name.lower()
    if "streaming_history_audio" in lower_name or "streaming_history_video" in lower_name:
        return "extended"
    if "streaminghistory" in lower_name:
        return "classic"
    if "endsong" in lower_name:
        return "end_song"
    return "unknown"


def content_type(record: dict, path: Path) -> str:
    lower_name = path.name.lower()
    if record.get("spotify_episode_uri") or record.get("episode_name") or "podcast" in lower_name:
        return "podcast"
    if "video" in lower_name:
        return "video"
    return "music"


def normalize_record(record: dict, path: Path) -> dict[str, object]:
    normalized: dict[str, object] = {
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_family": source_family(path),
        "content_type": content_type(record, path),
        "ts": record.get("ts") or record.get("endTime") or "",
        "username": record.get("username", ""),
        "platform": record.get("platform", ""),
        "ms_played": record.get("ms_played", record.get("msPlayed", "")),
        "conn_country": record.get("conn_country", ""),
        "ip_addr_decrypted": record.get("ip_addr_decrypted", record.get("ip_addr", "")),
        "user_agent_decrypted": record.get("user_agent_decrypted", ""),
        "master_metadata_track_name": record.get("master_metadata_track_name", record.get("trackName", "")),
        "master_metadata_album_artist_name": record.get(
            "master_metadata_album_artist_name",
            record.get("artistName", ""),
        ),
        "master_metadata_album_album_name": record.get(
            "master_metadata_album_album_name",
            record.get("albumName", ""),
        ),
        "spotify_track_uri": record.get("spotify_track_uri", ""),
        "episode_name": record.get("episode_name", record.get("episodeName", "")),
        "episode_show_name": record.get("episode_show_name", record.get("showName", "")),
        "spotify_episode_uri": record.get("spotify_episode_uri", ""),
        "reason_start": record.get("reason_start", ""),
        "reason_end": record.get("reason_end", ""),
        "shuffle": record.get("shuffle", ""),
        "skipped": record.get("skipped", ""),
        "offline": record.get("offline", ""),
        "offline_timestamp": record.get("offline_timestamp", ""),
        "incognito_mode": record.get("incognito_mode", ""),
    }
    return normalized


def write_outputs(rows: list[dict[str, object]]) -> dict[str, int]:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    audio_count = 0
    non_music_count = 0

    with MUSIC_OUTPUT.open("w", encoding="utf-8", newline="") as music_handle, NON_MUSIC_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as other_handle:
        music_writer = csv.DictWriter(music_handle, fieldnames=CANONICAL_FIELDS)
        other_writer = csv.DictWriter(other_handle, fieldnames=CANONICAL_FIELDS)
        music_writer.writeheader()
        other_writer.writeheader()

        for row in rows:
            if row["content_type"] == "music":
                music_writer.writerow(row)
                audio_count += 1
            else:
                other_writer.writerow(row)
                non_music_count += 1

    return {"music_rows": audio_count, "non_music_rows": non_music_count}


def main() -> int:
    files = history_files()
    if not files:
        print(f"No Spotify history JSON files found under {RAW_DIR}.")
        return 1

    rows: list[dict[str, object]] = []
    file_counts: dict[str, int] = {}
    for path in files:
        records = load_records(path)
        file_counts[path.relative_to(ROOT).as_posix()] = len(records)
        for record in records:
            rows.append(normalize_record(record, path))

    output_counts = write_outputs(rows)
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "history_files": [path.relative_to(ROOT).as_posix() for path in files],
                "file_record_counts": file_counts,
                "output_counts": output_counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Ingested {len(files)} files into {MUSIC_OUTPUT} and {NON_MUSIC_OUTPUT}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
