"""The local store — the vault.

Two things live here: the list of documents this machine knows about (with the
interface's state object for each), and the app-level library that every
document shares — references, styles, samples, property definitions, acronyms
and plot specs.

Deliberately plain `sqlite3`. ADR-W03 puts the Workbench on SQLAlchemy with
Alembic migrations over a proper relational schema; until the document model in
MODEL-001 §8 is settled, the interface's JSON *is* the contract, and pretending
otherwise would mean migrating a schema twice. `schema_version` is here so the
move is a migration rather than a rewrite.

What opening the vault does, in order:

1. If a database file exists, check it (`PRAGMA quick_check`). A file that
   will not open or does not pass is moved aside — never deleted — as
   `desk.sqlite.corrupt-<stamp>`, the newest backup that passes is restored in
   its place, and the library is re-applied from the JSON mirror, which is
   written on every library change and so is never older than any backup.
2. Take a backup of the (healthy) database into `backups/`, using SQLite's
   online backup API so the write-ahead log is included. The last
   `BACKUPS_KEPT` are kept.
3. Create any missing tables and run the migrations from the file's
   `schema_version` up to this module's. A file from a newer release is
   refused rather than silently downgraded.

Everything that happened is in `Store.notices`, so the interface can tell the
user instead of the user finding out later.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["Store", "SCHEMA_VERSION", "LIBRARY_KEYS", "BACKUPS_KEPT", "VaultTooNew"]

SCHEMA_VERSION = 2
BACKUPS_KEPT = 5

# App-scoped collections: they belong to the installation, not to one document.
# `templates` holds the user's own document templates — a house report shape,
# a centre's header and logo. Like the reference library, one is made once and
# used by every document after it, so it belongs to the installation.
# `peopleLib` and `orgLib` are the saved people and organisations a user reuses
# across papers — the same argument as the reference library: typed once on the
# installation, drawn on by every document. This is the settled place for them.
# `snippets` and `snippetFolders` are saved blocks of prose — the XPS
# experimental section, a data availability statement — with the folders they
# are filed under. Reused across papers by definition: copying one out of last
# year's manuscript is exactly the job they exist to abolish.
LIBRARY_KEYS = ("refs", "folders", "styleLib", "plots", "images",
                "samples", "sampleProps", "defs", "me", "templates",
                "peopleLib", "orgLib", "snippets", "snippetFolders")


class VaultTooNew(RuntimeError):
    """The database was written by a newer release than this one."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


# The schema as a fresh install creates it — always the current version. An
# older file is brought up to it by the migrations below, one step at a time.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    kind       TEXT NOT NULL,
    root       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    opened_at  TEXT,
    state      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS library (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx         INTEGER NOT NULL,
    at          TEXT NOT NULL,
    label       TEXT NOT NULL,
    by          TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'revision',
    snapshot    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS revisions_doc ON revisions(document_id, idx);
"""


def _migrate_to_2(c: sqlite3.Connection) -> None:
    """v2: documents remember when they were last opened, separately from when
    they were last saved, so the picker can order by what you were working on."""
    cols = {r["name"] for r in c.execute("PRAGMA table_info(documents)")}
    if "opened_at" not in cols:
        c.execute("ALTER TABLE documents ADD COLUMN opened_at TEXT")
    c.execute("UPDATE documents SET opened_at = updated_at WHERE opened_at IS NULL")


# target version -> the function that takes a database at (target - 1) to it.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    2: _migrate_to_2,
}


class Store:
    def __init__(self, path: Path, library_dir: Path | None = None,
                 backups_dir: Path | None = None):
        self.path = Path(path)
        self.library_dir = Path(library_dir) if library_dir else None
        self.backups_dir = Path(backups_dir) if backups_dir else self.path.parent / "backups"
        self.notices: list[str] = []
        self.backup_path: Path | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._check_and_recover()
        self.backup_path = self._backup()
        self._ensure_schema()

    # -- opening ------------------------------------------------------------

    def _check_and_recover(self) -> None:
        if not self.path.exists():
            return
        problem = self._problem_with(self.path)
        if problem is None:
            return
        aside = self._quarantine(problem)
        restored = self._restore_newest_backup()
        if restored:
            self.notices.append(
                f"The vault could not be read ({problem}). It was moved to {aside.name} and the "
                f"backup {restored.name} was restored in its place.")
        else:
            self.notices.append(
                f"The vault could not be read ({problem}). It was moved to {aside.name} and a "
                f"new, empty vault was started. Documents can be re-opened from their folders.")
        # Now there is a readable database; put the mirrored library on top of
        # whatever it holds. The mirror is written on every library change.
        self._ensure_schema()
        n = self.restore_library_from_mirror()
        if n:
            self.notices.append(
                f"The shared library was recovered from its JSON mirror ({n} sets).")

    @staticmethod
    def _problem_with(path: Path) -> str | None:
        """None if the file opens and passes an integrity check, else why not."""
        try:
            conn = sqlite3.connect(f"file:{path}?mode=rw", uri=True)
            try:
                row = conn.execute("PRAGMA quick_check").fetchone()
                if not row or row[0] != "ok":
                    return f"integrity check failed: {row[0] if row else 'no result'}"
                # A database that opens but is not ours at all.
                conn.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            return f"{exc.__class__.__name__}: {exc}"
        return None

    def _quarantine(self, reason: str) -> Path:
        aside = self.path.with_name(f"{self.path.name}.corrupt-{_stamp()}")
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(self.path) + suffix)
            if src.exists():
                os.replace(src, str(aside) + suffix)
        (aside.parent / (aside.name + ".txt")).write_text(
            f"Moved aside on {_now()} because: {reason}\n", encoding="utf-8")
        return aside

    def _restore_newest_backup(self) -> Path | None:
        for candidate in sorted(self.backups_dir.glob("desk-*.sqlite"), reverse=True):
            if self._problem_with(candidate) is None:
                shutil.copy2(candidate, self.path)
                return candidate
        return None

    def _backup(self) -> Path | None:
        """Copy the healthy database into backups/ with the online backup API,
        which includes anything still in the write-ahead log."""
        if not self.path.exists():
            return None
        try:
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            # Microseconds keep the names unique and their sort order honest
            # when the vault is opened twice in one second.
            dest = self.backups_dir / (
                f"desk-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}.sqlite")
            src = sqlite3.connect(self.path)
            try:
                dst = sqlite3.connect(dest)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()
            self._prune_backups()
            return dest
        except (sqlite3.Error, OSError) as exc:
            self.notices.append(f"Could not take a backup of the vault on opening: {exc}")
            return None

    def _prune_backups(self) -> None:
        backups = sorted(self.backups_dir.glob("desk-*.sqlite"))
        for old in backups[:-BACKUPS_KEPT]:
            try:
                old.unlink()
            except OSError:
                pass

    def _ensure_schema(self) -> None:
        with self._conn() as c:
            c.executescript(_SCHEMA)
            row = c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                c.execute("INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                          (str(SCHEMA_VERSION),))
                return
            current = int(row[0])
            if current > SCHEMA_VERSION:
                raise VaultTooNew(
                    f"The vault is schema version {current}; this release understands up to "
                    f"{SCHEMA_VERSION}. Update the application rather than opening it here.")
            for target in range(current + 1, SCHEMA_VERSION + 1):
                MIGRATIONS[target](c)
                c.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(target),))
                self.notices.append(f"Vault migrated to schema version {target}.")

    @property
    def schema_version(self) -> int:
        with self._conn() as c:
            return int(c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0])

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- documents ----------------------------------------------------------

    def create_document(self, title: str, kind: str, root: str, state: dict) -> str:
        doc_id = uuid.uuid4().hex
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO documents(id,title,kind,root,created_at,updated_at,opened_at,state)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (doc_id, title, kind, str(root), now, now, now, json.dumps(state)),
            )
        return doc_id

    def save_document(self, doc_id: str, state: dict) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE documents SET state=?, title=?, kind=?, updated_at=? WHERE id=?",
                (json.dumps(state), state.get("title", ""), state.get("kind", "publication"),
                 _now(), doc_id),
            )

    def mark_opened(self, doc_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE documents SET opened_at=? WHERE id=?", (_now(), doc_id))

    def get_document(self, doc_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"], "title": row["title"], "kind": row["kind"],
            "root": row["root"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "opened_at": row["opened_at"],
            "state": json.loads(row["state"]),
        }

    def find_by_root(self, root: str) -> dict | None:
        """The document registered at this folder, if any. Compared as real paths."""
        wanted = os.path.normcase(os.path.realpath(str(root)))
        for d in self.list_documents():
            if os.path.normcase(os.path.realpath(d["root"])) == wanted:
                return d
        return None

    def list_documents(self) -> list[dict]:
        """Most recently opened first; never-opened rows fall back to updated_at."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,title,kind,root,created_at,updated_at,opened_at FROM documents"
                " ORDER BY COALESCE(opened_at, updated_at) DESC, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Forgets the document. Never touches the folder on disk."""
        with self._conn() as c:
            cur = c.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        return cur.rowcount > 0

    # -- revisions ----------------------------------------------------------

    def add_revision(self, doc_id: str, revision: dict) -> int:
        with self._conn() as c:
            n = c.execute("SELECT COALESCE(MAX(idx),0) FROM revisions WHERE document_id=?",
                          (doc_id,)).fetchone()[0] + 1
            c.execute(
                "INSERT INTO revisions(id,document_id,idx,at,label,by,kind,snapshot)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (revision.get("id") or uuid.uuid4().hex, doc_id, n,
                 revision.get("at") or _now(), revision.get("label", f"Revision {n}"),
                 revision.get("by", "unknown"), revision.get("kind", "revision"),
                 json.dumps(revision.get("snapshot") or {})),
            )
        return n

    def list_revisions(self, doc_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,idx,at,label,by,kind FROM revisions WHERE document_id=? ORDER BY idx",
                (doc_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_revision(self, doc_id: str, index: int) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM revisions WHERE document_id=? AND idx=?", (doc_id, index)
            ).fetchone()
        if not row:
            return None
        out = dict(row)
        out["snapshot"] = json.loads(out.pop("snapshot"))
        return out

    # -- settings -----------------------------------------------------------
    # Installation-level preferences that are neither a document nor a library
    # set: the folders the Documents library shows, for instance. Kept in the
    # meta table under a `setting:` prefix, as JSON.

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._conn() as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", ("setting:" + key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except ValueError:
            return default

    def put_setting(self, key: str, value: Any) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO meta(key,value) VALUES (?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("setting:" + key, json.dumps(value)),
            )

    # -- library ------------------------------------------------------------

    def get_library(self) -> dict[str, Any]:
        with self._conn() as c:
            rows = c.execute("SELECT key,value FROM library").fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def put_library(self, values: dict[str, Any]) -> list[str]:
        written = []
        with self._conn() as c:
            for key, value in values.items():
                if key not in LIBRARY_KEYS:
                    continue
                c.execute(
                    "INSERT INTO library(key,value,updated_at) VALUES (?,?,?)"
                    " ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                    " updated_at=excluded.updated_at",
                    (key, json.dumps(value), _now()),
                )
                written.append(key)
        for key in written:
            self._mirror(key, values[key])
        return written

    def _mirror(self, key: str, value: Any) -> None:
        """`<library_dir>/<key>.json`, written whole then swapped into place so a
        crash mid-write leaves the previous copy, not half of the new one."""
        if self.library_dir is None:
            return
        try:
            self.library_dir.mkdir(parents=True, exist_ok=True)
            final = self.library_dir / f"{key}.json"
            tmp = self.library_dir / f".{key}.json.tmp"
            tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, final)
        except OSError as exc:
            self.notices.append(f"Could not mirror the library set '{key}' to disk: {exc}")

    def restore_library_from_mirror(self) -> int:
        """Re-apply every mirrored set. Returns how many were applied."""
        if self.library_dir is None or not self.library_dir.exists():
            return 0
        values: dict[str, Any] = {}
        for key in LIBRARY_KEYS:
            f = self.library_dir / f"{key}.json"
            if not f.exists():
                continue
            try:
                # utf-8-sig: the mirror is meant to be editable by hand, so a
                # byte-order mark from an editor must not lose the whole set.
                values[key] = json.loads(f.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as exc:
                self.notices.append(f"The mirrored library set '{key}' could not be read: {exc}")
        if not values:
            return 0
        # Write to the database only; the mirror is already what we read.
        with self._conn() as c:
            for key, value in values.items():
                c.execute(
                    "INSERT INTO library(key,value,updated_at) VALUES (?,?,?)"
                    " ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                    " updated_at=excluded.updated_at",
                    (key, json.dumps(value), _now()),
                )
        return len(values)

    def split_state(self, state: dict) -> tuple[dict, dict]:
        """Separate a state object into (document-scoped, library-scoped)."""
        library = {k: state[k] for k in LIBRARY_KEYS if k in state}
        document = {k: v for k, v in state.items() if k not in LIBRARY_KEYS}
        return document, library

    def merge_state(self, document: dict) -> dict:
        """Put the library back on top of a document's own state."""
        merged = dict(document)
        merged.update(self.get_library())
        return merged
