"""Offline tests for safe GitHub Release snapshot refreshes."""
import hashlib
from pathlib import Path

import pytest

import anac_cloud_warehouse as cloud


class FakeDownload:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.data


def asset(data, version=11):
    return {
        "id": version,
        "url": "https://github.com/example/download/anac.duckdb",
        "size": len(data),
        "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def test_first_download_and_cached_reuse(tmp_path, monkeypatch):
    data = b"a-valid-snapshot"
    destination = tmp_path / "anac.duckdb"
    downloads = []

    def get(url, **kwargs):
        downloads.append(url)
        return FakeDownload(data)

    monkeypatch.setattr(cloud.requests, "get", get)
    monkeypatch.setattr(cloud, "_verify_database", lambda path: None)
    assert cloud.ensure_snapshot(asset(data), destination) == "11"
    assert destination.read_bytes() == data
    assert cloud.ensure_snapshot(asset(data), destination) == "11"
    assert len(downloads) == 1


def test_new_asset_replaces_previous(tmp_path, monkeypatch):
    old = b"previous-snapshot"
    new = b"refreshed-snapshot"
    dest = tmp_path / "anac.duckdb"
    fetched = iter([old, new])
    monkeypatch.setattr(cloud.requests, "get", lambda *a, **kw: FakeDownload(next(fetched)))
    monkeypatch.setattr(cloud, "_verify_database", lambda path: None)
    cloud.ensure_snapshot(asset(old, 11), dest)
    assert cloud.ensure_snapshot(asset(new, 12), dest) == "12"
    assert dest.read_bytes() == new


def test_hash_mismatch_preserves_previous_snapshot(tmp_path, monkeypatch):
    old = b"previous-snapshot"
    new = b"different-snapshot"
    dest = tmp_path / "anac.duckdb"
    fetched = iter([old, new])
    monkeypatch.setattr(cloud.requests, "get", lambda *a, **kw: FakeDownload(next(fetched)))
    monkeypatch.setattr(cloud, "_verify_database", lambda path: None)
    cloud.ensure_snapshot(asset(old, 11), dest)
    wrong_digest_asset = asset(b"wrong-hash", 12)
    wrong_digest_asset["size"] = len(new)
    with pytest.raises(RuntimeError, match="SHA-256"):
        cloud.ensure_snapshot(wrong_digest_asset, dest)
    assert dest.read_bytes() == old


def test_schema_verification_failure_preserves_old_snapshot(tmp_path, monkeypatch):
    old, new = b"old-good", b"new-broken"
    dest = tmp_path / "anac.duckdb"
    fetched = iter([old, new])
    monkeypatch.setattr(cloud.requests, "get", lambda *a, **kw: FakeDownload(next(fetched)))
    monkeypatch.setattr(cloud, "_verify_database", lambda p: None)
    cloud.ensure_snapshot(asset(old, 11), dest)

    def fail(_):
        raise RuntimeError("Invalid DuckDB")

    monkeypatch.setattr(cloud, "_verify_database", fail)
    with pytest.raises(RuntimeError, match="Invalid DuckDB"):
        cloud.ensure_snapshot(asset(new, 12), dest)
    assert dest.read_bytes() == old
