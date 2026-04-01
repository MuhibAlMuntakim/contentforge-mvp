"""
SQLite persistence layer.

Stores content packages, platform payloads, publish results, and audit reports.
Designed for easy future migration to PostgreSQL or another DB — all SQL is
isolated here behind a clean Python API.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.models import (
    AuditReport,
    ContentPackage,
    Platform,
    PlatformPayload,
    PublishResult,
)

from config.settings import DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    """SQLite-backed storage for all publishing data."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    # ── Connection management ────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Schema initialization ────────────────────────────────────────────

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS content_packages (
                    content_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS platform_payloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (content_id) REFERENCES content_packages(content_id)
                );

                CREATE TABLE IF NOT EXISTS publish_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (content_id) REFERENCES content_packages(content_id)
                );

                CREATE TABLE IF NOT EXISTS audit_reports (
                    report_id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (content_id) REFERENCES content_packages(content_id)
                );

                CREATE INDEX IF NOT EXISTS idx_payloads_content
                    ON platform_payloads(content_id);
                CREATE INDEX IF NOT EXISTS idx_results_content
                    ON publish_results(content_id);
                CREATE INDEX IF NOT EXISTS idx_reports_content
                    ON audit_reports(content_id);
            """)

    # ── Content Packages ─────────────────────────────────────────────────

    def save_content_package(self, package: ContentPackage) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO content_packages
                   (content_id, data_json, created_at) VALUES (?, ?, ?)""",
                (package.content_id, package.model_dump_json(), _now_iso()),
            )

    def get_content_package(self, content_id: str) -> Optional[ContentPackage]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data_json FROM content_packages WHERE content_id = ?",
                (content_id,),
            ).fetchone()
        if row:
            return ContentPackage.model_validate_json(row["data_json"])
        return None

    def list_content_packages(self, limit: int = 50) -> list[ContentPackage]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data_json FROM content_packages ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ContentPackage.model_validate_json(r["data_json"]) for r in rows]

    # ── Platform Payloads ────────────────────────────────────────────────

    def save_platform_payload(self, payload: PlatformPayload) -> None:
        with self._conn() as conn:
            # Upsert: delete existing for same content_id + platform, then insert
            conn.execute(
                """DELETE FROM platform_payloads
                   WHERE content_id = ? AND platform = ?""",
                (payload.content_id, payload.platform.value),
            )
            conn.execute(
                """INSERT INTO platform_payloads
                   (content_id, platform, payload_json, created_at) VALUES (?, ?, ?, ?)""",
                (payload.content_id, payload.platform.value,
                 payload.model_dump_json(), _now_iso()),
            )

    def get_platform_payloads(
        self, content_id: str, platform: Optional[Platform] = None
    ) -> list[PlatformPayload]:
        with self._conn() as conn:
            if platform:
                rows = conn.execute(
                    """SELECT payload_json FROM platform_payloads
                       WHERE content_id = ? AND platform = ?""",
                    (content_id, platform.value),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM platform_payloads WHERE content_id = ?",
                    (content_id,),
                ).fetchall()
        return [PlatformPayload.model_validate_json(r["payload_json"]) for r in rows]

    # ── Publish Results ──────────────────────────────────────────────────

    def save_publish_result(self, result: PublishResult) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO publish_results
                   (content_id, platform, result_json, created_at) VALUES (?, ?, ?, ?)""",
                (result.content_id, result.platform.value,
                 result.model_dump_json(), _now_iso()),
            )

    def get_publish_results(self, content_id: str) -> list[PublishResult]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT result_json FROM publish_results
                   WHERE content_id = ? ORDER BY created_at""",
                (content_id,),
            ).fetchall()
        return [PublishResult.model_validate_json(r["result_json"]) for r in rows]

    # ── Audit Reports ────────────────────────────────────────────────────

    def save_audit_report(self, report: AuditReport) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO audit_reports
                   (report_id, content_id, report_json, created_at) VALUES (?, ?, ?, ?)""",
                (report.report_id, report.content_id,
                 report.model_dump_json(), _now_iso()),
            )

    def get_audit_report(self, report_id: str) -> Optional[AuditReport]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT report_json FROM audit_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
        if row:
            return AuditReport.model_validate_json(row["report_json"])
        return None

    def get_audit_reports_for_content(self, content_id: str) -> list[AuditReport]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT report_json FROM audit_reports
                   WHERE content_id = ? ORDER BY created_at DESC""",
                (content_id,),
            ).fetchall()
        return [AuditReport.model_validate_json(r["report_json"]) for r in rows]

    def list_audit_reports(self, limit: int = 50) -> list[AuditReport]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT report_json FROM audit_reports ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [AuditReport.model_validate_json(r["report_json"]) for r in rows]
