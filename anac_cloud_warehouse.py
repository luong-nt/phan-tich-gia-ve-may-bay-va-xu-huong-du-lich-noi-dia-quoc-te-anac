"""Download and validate the published ANAC DuckDB snapshot for Streamlit.

Public GitHub Releases are used as the single source of the deployed snapshot.
No AWS credentials or personal GitHub token are needed for this public repo.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

import duckdb
import requests

GITHUB_REPO = "luong-nt/phan-tich-gia-ve-may-bay-va-xu-huong-du-lich-noi-dia-quoc-te-anac"
RELEASE_TAG = "warehouse-current"
MAX_BYTES = 512 * 1024 * 1024  # Reject unexpectedly large assets (512 MiB).
_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "anac-portfolio-dashboard"}
_LOCK = Lock()


def fetch_release_asset() -> dict:
    """Fetch current public release metadata (cache this in Streamlit)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{RELEASE_TAG}"
    response = requests.get(url, headers=_HEADERS, timeout=(10, 25))
    response.raise_for_status()
    release = response.json()
    matches = [a for a in release.get("assets", []) if a.get("name") == "anac.duckdb"]
    if len(matches) != 1:
        raise RuntimeError("Release warehouse-current must contain exactly one anac.duckdb asset")
    asset = matches[0]
    size = int(asset.get("size", 0))
    if not 1024 <= size <= MAX_BYTES:
        raise RuntimeError(f"Unexpected DuckDB size in release: {size} bytes")
    download_url = str(asset.get("browser_download_url", ""))
    expected_prefix = f"https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/"
    if not download_url.startswith(expected_prefix):
        raise RuntimeError("Unrecognized GitHub Release download URL")
    digest = asset.get("digest") or ""
    if digest and not (isinstance(digest, str) and digest.startswith("sha256:") and len(digest) == 71):
        raise RuntimeError("Unsupported GitHub asset digest")
    return {
        "id": int(asset["id"]),
        "url": download_url,
        "size": size,
        "digest": digest,
    }


def _read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}


def _verify_database(path: Path) -> None:
    """Reject corrupt snapshots or snapshots missing core DW objects."""
    with duckdb.connect(str(path), read_only=True) as con:
        rows = con.execute("SELECT COUNT(*) FROM fact_airfare_route_monthly").fetchone()[0]
        months = con.execute("SELECT COUNT(*) FROM vw_monthly_kpi").fetchone()[0]
    if rows <= 0 or months <= 0:
        raise RuntimeError("Downloaded DuckDB snapshot is empty or invalid")


def ensure_snapshot(asset: dict, destination: Path) -> str:
    """Download if the GitHub asset ID changed; verify before atomic replacement.

    Returns a stable asset ID to use as a Streamlit data-cache version key.
    If downloading/validation fails, the existing snapshot is left untouched.
    """
    destination = Path(destination)
    state_path = destination.with_suffix(".release.json")
    asset_id = str(asset["id"])
    with _LOCK:
        state = _read_state(state_path)
        if (destination.is_file()
            and state.get("asset_id") == asset_id
            and destination.stat().st_size == int(asset["size"])):
            return asset_id

        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp_name = None
        try:
            with NamedTemporaryFile(mode="wb", prefix=".anac-download-", suffix=".duckdb",
                                    dir=destination.parent, delete=False) as tmp:
                tmp_name = tmp.name
                sha256 = hashlib.sha256()
                total = 0
                with requests.get(asset["url"], headers={"User-Agent": _HEADERS["User-Agent"]},
                                  stream=True, timeout=(15, 180)) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise RuntimeError("Download exceeded maximum expected size")
                        sha256.update(chunk)
                        tmp.write(chunk)
            if total != int(asset["size"]):
                raise RuntimeError(f"Incomplete download: received {total}, expected {asset['size']}")
            expected_digest = str(asset.get("digest") or "")
            if expected_digest and f"sha256:{sha256.hexdigest()}" != expected_digest:
                raise RuntimeError("GitHub Release asset SHA-256 verification failed")
            _verify_database(Path(tmp_name))
            # Do not overwrite a valid snapshot until the replacement has passed checks.
            os.replace(tmp_name, destination)
            tmp_name = None
            state_path.write_text(json.dumps({"asset_id": asset_id, "sha256": sha256.hexdigest()}),
                                  encoding="utf-8")
            return asset_id
        finally:
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)
