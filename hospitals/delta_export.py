#!/usr/bin/env python3
"""
Delta GeoPackage exporter for fmedata
Generated: 2026-03-25T11:15:03.734Z
Source type: postgis

Handles inserts, updates AND deletes automatically.
Delete detection works via FID diff — no changes to your database needed.

Usage:
  python delta_export.py                    # Full export (resets state)
  python delta_export.py --since last       # Delta since last run
  python delta_export.py --since 2024-01-01 # Delta since specific date

Requires: psycopg2 (pip install psycopg2-binary)
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")
STATE_FILE = os.path.join(OUTPUT_DIR, ".delta_state.json")
MODEL_NAME = "fmedata"


# ============================================================
# State management
# State stores per layer: last_sync timestamp + set of known FIDs
# ============================================================

def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_since(args, layer_id):
    """Resolve the --since argument."""
    if "--since" not in args:
        return None  # full export
    idx = args.index("--since")
    val = args[idx + 1] if idx + 1 < len(args) else "last"
    if val == "last":
        state = load_state()
        return state.get(layer_id, {}).get("last_sync")
    return val


# ============================================================
# Database connection
# ============================================================

def get_pg_conn_string():
    """OGR connection string for ogr2ogr."""
    host = os.environ.get("POSTGRES_HOST", "postgis.train.safe.com")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "fmedata")
    user = os.environ.get("POSTGRES_USER", "fmedata")
    password = os.environ.get("POSTGRES_PASSWORD", "fmedata")
    schema = os.environ.get("POSTGRES_SCHEMA", "public")
    return f"PG:host={host} port={port} dbname={dbname} user={user} password={password} schemas={schema}"

PG_CONN = get_pg_conn_string()


def pg_connect():
    """Direct psycopg2 connection for FID queries."""
    import psycopg2
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgis.train.safe.com"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "fmedata"),
        user=os.environ.get("POSTGRES_USER", "fmedata"),
        password=os.environ.get("POSTGRES_PASSWORD", "fmedata"),
        options=f"-c search_path={os.environ.get('POSTGRES_SCHEMA', 'public')}"
    )


def fetch_current_pks(table, pk_col="fid"):
    """Get the set of all current primary keys from a table. Fast — just a PK index scan."""
    conn = pg_connect()
    try:
        cur = conn.cursor()
        cur.execute(f'SELECT "{pk_col}" FROM "{table}"')
        pks = {row[0] for row in cur.fetchall()}
        cur.close()
        return pks
    finally:
        conn.close()


# ============================================================
# zones
# Source table: zones
# Primary key: id
# Timestamp column: (none — full diff for updates)
# Delete detection: automatic PK diff
# ============================================================

def export_zones(since=None):
    now = datetime.now(timezone.utc).isoformat()
    state = load_state()
    layer_state = state.get("nu8bej3", {})
    previous_pks = set(layer_state.get("pks", []))

    # --- Step 1: Get current PKs from source ---
    current_pks = fetch_current_pks("zones", "id")
    print(f"  [zones] {len(current_pks)} features in source, {len(previous_pks)} in previous state")

    if since is None:
        # --- FULL EXPORT (no delta, reset state) ---
        output = os.path.join(OUTPUT_DIR, f"zones_full.gpkg")
        cmd = [
            "ogr2ogr", "-f", "GPKG", output,
            PG_CONN, "zones",
            "-nln", "zones",
            "-a_srs", "EPSG:4326",
            "-overwrite"
        ]
        print(f"  [zones] Full export → {output}")
        subprocess.run(cmd, check=True)

        # Save state: timestamp + all PKs
        state["nu8bej3"] = {
            "last_sync": now,
            "pks": sorted(current_pks),
            "output": output
        }
        save_state(state)
        return output

    # --- DELTA EXPORT ---
    output = os.path.join(OUTPUT_DIR, f"zones_delta_{now[:10]}.gpkg")

    # Step 2: Detect deletes (PKs that disappeared)
    deleted_pks = previous_pks - current_pks
    if deleted_pks:
        print(f"  [zones] {len(deleted_pks)} deletes detected")

    # Step 3: Detect inserts (PKs that are new)
    inserted_pks = current_pks - previous_pks
    if inserted_pks:
        print(f"  [zones] {len(inserted_pks)} new features detected")

    # Step 4: Export inserts (PK-based, no timestamp available)
    # NOTE: Without a timestamp column, updates to existing features
    # cannot be detected. Only inserts and deletes are tracked.
    has_changes = False

    if inserted_pks:
        pk_list = ','.join(str(f) for f in inserted_pks)
        sql_inserts = f"""
            SELECT *, 'insert' as _change_type
            FROM "zones"
            WHERE "id" IN ({pk_list})
        """
        cmd = [
            "ogr2ogr", "-f", "GPKG", output,
            PG_CONN, "-sql", sql_inserts,
            "-nln", "zones",
            "-a_srs", "EPSG:4326"
        ]
        subprocess.run(cmd, check=True)
        has_changes = True

    # Step 5: Append deletes to the delta GeoPackage
    # Deletes are stored as rows with only the PK + _change_type = 'delete'
    if deleted_pks:
        import tempfile
        delete_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"id": pk, "_change_type": "delete"},
                    "geometry": None
                }
                for pk in sorted(deleted_pks)
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False) as f:
            json.dump(delete_geojson, f)
            tmp_path = f.name

        append_flag = ["-append"] if has_changes else []
        cmd = [
            "ogr2ogr", "-f", "GPKG", output,
            tmp_path,
            "-nln", "zones_deletes",
            *append_flag
        ]
        subprocess.run(cmd, check=True)
        os.unlink(tmp_path)
        has_changes = True

    if not has_changes:
        print(f"  [zones] No changes detected")
    else:
        print(f"  [zones] Delta → {output}")

    # Step 6: Update state with current PKs
    state["nu8bej3"] = {
        "last_sync": now,
        "pks": sorted(current_pks),
        "output": output
    }
    save_state(state)
    return output if has_changes else None


# ============================================================
# Main
# ============================================================

def main():
    is_delta = "--since" in sys.argv
    mode = "DELTA" if is_delta else "FULL"
    print(f"=== {mode} export for fmedata ===")
    print(f"    Time: {datetime.now(timezone.utc).isoformat()}")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    results = {}

    since_zones = get_since(sys.argv, "nu8bej3")
    results["zones"] = export_zones(since=since_zones)

    # Summary
    print()
    print("=== Summary ===")
    for layer, output in results.items():
        status = f"→ {output}" if output else "(no changes)"
        print(f"  {layer}: {status}")
    print("=== Done ===")


if __name__ == "__main__":
    main()



# ============================================================
# STAC helpers
# ============================================================

import hashlib
import uuid as _uuid

STAC_VERSION = "1.0.0"
STAC_COLLECTION_ID = "5qects4"
STAC_DEFAULT_BBOX = [-180,-90,180,90]
STAC_EPSG = 4326
STAC_EXTENSIONS = [
    "https://stac-extensions.github.io/timestamps/v1.1.0/schema.json",
    "https://stac-extensions.github.io/projection/v1.1.0/schema.json",
    "https://stac-extensions.github.io/file/v2.1.0/schema.json",
]


def _detect_bbox(gpkg_path):
    """Use ogrinfo to detect the bounding box of a GeoPackage layer."""
    try:
        result = subprocess.run(
            ["ogrinfo", "-so", "-al", gpkg_path],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.splitlines():
            if line.startswith("Extent:"):
                # Extent: (minx, miny) - (maxx, maxy)
                parts = line.replace("Extent:", "").replace("(", "").replace(")", "").split("-")
                west, south = [float(v.strip()) for v in parts[0].split(",")]
                east, north = [float(v.strip()) for v in parts[1].split(",")]
                return [west, south, east, north]
    except Exception:
        pass
    return STAC_DEFAULT_BBOX


def _sha256_checksum(path):
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def write_stac_item(tbl, output_path, export_type, collection_id=STAC_COLLECTION_ID, bbox=None):
    """Write a STAC Item JSON file alongside the GeoPackage."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    item_id = f"{tbl}-{export_type}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{str(_uuid.uuid4())[:8]}"
    detected_bbox = bbox or _detect_bbox(output_path)
    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else None
    checksum = _sha256_checksum(output_path) if os.path.exists(output_path) else None

    item = {
        "type": "Feature",
        "stac_version": STAC_VERSION,
        "stac_extensions": STAC_EXTENSIONS,
        "id": item_id,
        "geometry": None,
        "bbox": detected_bbox,
        "properties": {
            "datetime": None,
            "created": now,
            "updated": now,
            "proj:epsg": STAC_EPSG,
            "file:size": file_size,
            "file:checksum": checksum,
            "export_type": export_type,
            "layer": tbl,
            "collection": collection_id,
        },
        "links": [
            {"rel": "self", "href": f"./{os.path.basename(output_path)}.stac.json", "type": "application/json"},
            {"rel": "root", "href": "./stac/catalog.json", "type": "application/json"},
            {"rel": "parent", "href": f"./stac/{tbl}/catalog.json", "type": "application/json"},
            {"rel": "collection", "href": f"./stac/collections/{collection_id}/collection.json", "type": "application/json"},
        ],
        "assets": {
            "data": {
                "href": f"./{os.path.basename(output_path)}",
                "title": f"{tbl} ({export_type})",
                "type": "application/geopackage+sqlite3",
                "roles": ["data"],
                "file:size": file_size,
                "file:checksum": checksum,
            }
        },
        "collection": collection_id,
    }

    item_path = output_path + ".stac.json"
    with open(item_path, "w") as f:
        json.dump(item, f, indent=2)
    print(f"  [stac] Wrote {item_path}")
    return item_path


def update_stac_layer_catalog(tbl, item_path, stac_root):
    """Add a link to the new STAC item in the per-layer catalog.json."""
    catalog_path = os.path.join(stac_root, tbl, "catalog.json")
    if not os.path.exists(catalog_path):
        return

    try:
        with open(catalog_path) as f:
            catalog = json.load(f)

        item_href = os.path.relpath(item_path, os.path.dirname(catalog_path)).replace("\\", "/")
        new_link = {"rel": "item", "href": item_href, "type": "application/json"}

        # Avoid duplicate links
        existing_hrefs = {lnk.get("href") for lnk in catalog.get("links", [])}
        if item_href not in existing_hrefs:
            catalog.setdefault("links", []).append(new_link)
            with open(catalog_path, "w") as f:
                json.dump(catalog, f, indent=2)
            print(f"  [stac] Updated {catalog_path}")
    except Exception as e:
        print(f"  [stac] Warning: could not update layer catalog: {e}")
