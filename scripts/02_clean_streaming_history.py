from __future__ import annotations

import csv
import hashlib
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TZ = ZoneInfo("America/Mexico_City")
INPUT_PATH = ROOT / "data" / "interim" / "streaming_history_audio_raw.csv"
PRIVATE_OUTPUT = ROOT / "outputs" / "private" / "streaming_history_eventlevel_clean.csv"
PUBLIC_SAFE_OUTPUT = ROOT / "data" / "processed" / "public_safe" / "streaming_history_monthly_track_aggregate.csv"
SAMPLE_OUTPUT = ROOT / "data" / "processed" / "samples" / "sample_streaming_history_synthetic.csv"
MIN_MS_PLAYED = 30000

SENSITIVE_COLUMNS = {
    "username",
    "ip_addr_decrypted",
    "user_agent_decrypted",
    "conn_country",
    "incognito_mode",
    "offline_timestamp",
    "ts",
}

PRIVATE_FIELDS = [
    "track_id_hash",
    "spotify_track_uri_hash",
    "track_name",
    "artist_name",
    "album_name",
    "date",
    "date_year",
    "date_month",
    "year_month",
    "hour",
    "ms_played",
    "minutes_played",
    "platform",
    "reason_start",
    "reason_end",
    "shuffle",
    "skipped",
    "offline",
    "source_file",
    "source_family",
]

PUBLIC_SAFE_FIELDS = [
    "date_year",
    "date_month",
    "year_month",
    "track_id_hash",
    "spotify_track_uri_hash",
    "track_name",
    "artist_name",
    "album_name",
    "minutes_played",
    "n_streams",
]


def normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_timestamp(raw_value: str) -> datetime | None:
    if not raw_value:
        return None

    value = raw_value.strip()
    try:
        if "T" in value:
            utc_value = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(utc_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
            return parsed.astimezone(LOCAL_TZ)
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
        return parsed.replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None


def boolish(value: str) -> str:
    lowered = str(value).strip().lower()
    if lowered in {"true", "1"}:
        return "true"
    if lowered in {"false", "0"}:
        return "false"
    return ""


def build_track_hash(track_name: str, artist_name: str, album_name: str, spotify_track_uri: str) -> tuple[str, str]:
    uri = spotify_track_uri.strip()
    uri_hash = sha256_text(uri) if uri else ""
    if uri:
        return sha256_text(f"uri::{uri}"), uri_hash

    fallback = "meta::" + "||".join(
        [
            normalize_text(track_name),
            normalize_text(artist_name),
            normalize_text(album_name),
        ]
    )
    return sha256_text(fallback), uri_hash


def read_rows() -> list[dict[str, str]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing interim input: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def clean_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    cleaned: list[dict[str, object]] = []
    for row in rows:
        try:
            ms_played = int(float(row.get("ms_played") or 0))
        except ValueError:
            continue

        if ms_played < MIN_MS_PLAYED:
            continue

        local_dt = parse_timestamp(row.get("ts", ""))
        if local_dt is None:
            continue

        track_name = (row.get("master_metadata_track_name") or "").strip()
        artist_name = (row.get("master_metadata_album_artist_name") or "").strip()
        album_name = (row.get("master_metadata_album_album_name") or "").strip()
        spotify_track_uri = (row.get("spotify_track_uri") or "").strip()
        track_id_hash, uri_hash = build_track_hash(track_name, artist_name, album_name, spotify_track_uri)

        cleaned.append(
            {
                "track_id_hash": track_id_hash,
                "spotify_track_uri_hash": uri_hash,
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name,
                "date": local_dt.date().isoformat(),
                "date_year": str(local_dt.year),
                "date_month": f"{local_dt.month:02d}",
                "year_month": f"{local_dt.year}-{local_dt.month:02d}",
                "hour": f"{local_dt.hour:02d}",
                "ms_played": ms_played,
                "minutes_played": round(ms_played / 60000, 4),
                "platform": (row.get("platform") or "").strip(),
                "reason_start": (row.get("reason_start") or "").strip(),
                "reason_end": (row.get("reason_end") or "").strip(),
                "shuffle": boolish(row.get("shuffle", "")),
                "skipped": boolish(row.get("skipped", "")),
                "offline": boolish(row.get("offline", "")),
                "source_file": (row.get("source_file") or "").strip(),
                "source_family": (row.get("source_family") or "").strip(),
            }
        )

    return cleaned


def write_private_clean(rows: list[dict[str, object]]) -> None:
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with PRIVATE_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRIVATE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in PRIVATE_FIELDS})


def aggregate_public_safe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: OrderedDict[tuple[str, ...], dict[str, object]] = OrderedDict()
    for row in rows:
        key = (
            str(row["date_year"]),
            str(row["date_month"]),
            str(row["year_month"]),
            str(row["track_id_hash"]),
            str(row["spotify_track_uri_hash"]),
            str(row["track_name"]),
            str(row["artist_name"]),
            str(row["album_name"]),
        )
        if key not in grouped:
            grouped[key] = {
                "date_year": row["date_year"],
                "date_month": row["date_month"],
                "year_month": row["year_month"],
                "track_id_hash": row["track_id_hash"],
                "spotify_track_uri_hash": row["spotify_track_uri_hash"],
                "track_name": row["track_name"],
                "artist_name": row["artist_name"],
                "album_name": row["album_name"],
                "minutes_played": 0.0,
                "n_streams": 0,
            }
        grouped[key]["minutes_played"] = round(float(grouped[key]["minutes_played"]) + float(row["minutes_played"]), 4)
        grouped[key]["n_streams"] = int(grouped[key]["n_streams"]) + 1

    return list(grouped.values())


def validate_public_safe(rows: list[dict[str, object]]) -> None:
    for forbidden in SENSITIVE_COLUMNS:
        if forbidden in PUBLIC_SAFE_FIELDS:
            raise ValueError(f"Forbidden column present in public-safe schema: {forbidden}")
    if any("date" == field or "hour" == field for field in PUBLIC_SAFE_FIELDS):
        raise ValueError("Public-safe output must not include exact day or hour fields.")

    for row in rows[:10]:
        for forbidden in SENSITIVE_COLUMNS:
            if forbidden in row and row[forbidden]:
                raise ValueError(f"Public-safe rows still contain sensitive data: {forbidden}")


def write_public_safe(rows: list[dict[str, object]]) -> None:
    PUBLIC_SAFE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    validate_public_safe(rows)
    with PUBLIC_SAFE_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PUBLIC_SAFE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in PUBLIC_SAFE_FIELDS})


def write_synthetic_sample(rows: list[dict[str, object]]) -> None:
    SAMPLE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sample_rows = rows[:100]
    track_map: dict[str, str] = {}
    artist_map: dict[str, str] = {}
    album_map: dict[str, str] = {}

    with SAMPLE_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PUBLIC_SAFE_FIELDS)
        writer.writeheader()

        for row in sample_rows:
            track_key = str(row["track_id_hash"])
            artist_key = str(row["artist_name"])
            album_key = str(row["album_name"])

            if track_key not in track_map:
                track_map[track_key] = f"track_{len(track_map) + 1:03d}"
            if artist_key not in artist_map:
                artist_map[artist_key] = f"artist_{len(artist_map) + 1:03d}"
            if album_key not in album_map:
                album_map[album_key] = f"album_{len(album_map) + 1:03d}"

            synthetic_row = dict(row)
            synthetic_row["track_name"] = track_map[track_key]
            synthetic_row["artist_name"] = artist_map[artist_key]
            synthetic_row["album_name"] = album_map[album_key]
            writer.writerow({field: synthetic_row.get(field, "") for field in PUBLIC_SAFE_FIELDS})


def main() -> int:
    rows = read_rows()
    cleaned_rows = clean_rows(rows)
    if not cleaned_rows:
        print("No valid listening events remained after cleaning.")
        return 1

    write_private_clean(cleaned_rows)
    public_safe_rows = aggregate_public_safe(cleaned_rows)
    write_public_safe(public_safe_rows)
    write_synthetic_sample(public_safe_rows)

    print(
        "Cleaned audio history written to "
        f"{PRIVATE_OUTPUT} and monthly public-safe aggregates written to {PUBLIC_SAFE_OUTPUT}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
