"""SQLite-based storage for the repo index."""

import sqlite3
import os
from typing import List, Dict, Any, Optional


class RepoIndex:
    """SQLite-based storage for indexed code structures."""

    def __init__(self, path: str = ".repo-index/index.db"):
        self.path = path
        self.ensure_dirs()
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self._create_tables()

    def ensure_dirs(self):
        """Ensure the directory for the index exists."""
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)

    def _create_tables(self):
        """Create the database tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lineno INTEGER NOT NULL,
                col_offset INTEGER NOT NULL,
                end_lineno INTEGER NOT NULL,
                end_col_offset INTEGER NOT NULL,
                parent TEXT,
                file_path TEXT
            );
            CREATE TABLE IF NOT EXISTS constants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lineno INTEGER NOT NULL,
                col_offset INTEGER NOT NULL,
                parent TEXT,
                file_path TEXT
            );
            CREATE TABLE IF NOT EXISTS variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lineno INTEGER NOT NULL,
                col_offset INTEGER NOT NULL,
                parent TEXT,
                file_path TEXT
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL
            );
        """)
        self.conn.commit()

    def clear(self):
        """Remove all indexed data. Call before a full re-index so re-running
        `index` doesn't accumulate duplicate rows for unchanged files."""
        self.conn.executescript("""
            DELETE FROM methods;
            DELETE FROM constants;
            DELETE FROM variables;
            DELETE FROM files;
        """)
        self.conn.commit()

    def add_file(self, file_path: str, source: str):
        """Index all methods, constants, and variables from a file."""
        from .parser import parse_source, extract_nodes

        tree = parse_source(source)
        nodes = extract_nodes(tree, source)

        # Add file record
        self.conn.execute(
            "INSERT OR IGNORE INTO files (path) VALUES (?)",
            (file_path,),
        )

        # Index methods
        for method in nodes["methods"]:
            self.conn.execute(
                "INSERT INTO methods (name, lineno, col_offset, end_lineno, end_col_offset, parent, file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (method["name"], method["lineno"], method["col_offset"], method["end_lineno"], method["end_col_offset"], method.get("parent"), file_path),
            )

        # Index constants
        for constant in nodes["constants"]:
            self.conn.execute(
                "INSERT INTO constants (name, lineno, col_offset, parent, file_path) VALUES (?, ?, ?, ?, ?)",
                (constant["name"], constant["lineno"], constant["col_offset"], constant.get("parent"), file_path),
            )

        # Index variables (currently empty from parser, but kept for future use)
        # for variable in nodes["variables"]:
        #     self.conn.execute(
        #         "INSERT INTO variables (name, lineno, col_offset, parent, file_path) VALUES (?, ?, ?, ?, ?)",
        #         (variable["name"], variable["lineno"], variable["col_offset"], variable.get("parent"), file_path),
        #     )

        self.conn.commit()

    def search(self, query: str, search_type: str = "all") -> List[Dict[str, Any]]:
        """Search the index for methods, constants, or variables matching a query."""
        results = []

        query_lower = query.lower()

        if search_type in ("methods", "all"):
            rows = self.conn.execute(
                "SELECT name, lineno, col_offset, end_lineno, end_col_offset, parent, file_path FROM methods WHERE LOWER(name) LIKE ?",
                (f"%{query_lower}%",),
            ).fetchall()
            for row in rows:
                results.append({
                    "type": "method",
                    "name": row[0],
                    "lineno": row[1],
                    "col_offset": row[2],
                    "end_lineno": row[3],
                    "end_col_offset": row[4],
                    "parent": row[5],
                    "file_path": row[6],
                })

        if search_type in ("constants", "all"):
            rows = self.conn.execute(
                "SELECT name, lineno, col_offset, parent, file_path FROM constants WHERE LOWER(name) LIKE ?",
                (f"%{query_lower}%",),
            ).fetchall()
            for row in rows:
                results.append({
                    "type": "constant",
                    "name": row[0],
                    "lineno": row[1],
                    "col_offset": row[2],
                    "parent": row[3],
                    "file_path": row[4],
                })

        if search_type in ("variables", "all"):
            rows = self.conn.execute(
                "SELECT name, lineno, col_offset, parent, file_path FROM variables WHERE LOWER(name) LIKE ?",
                (f"%{query_lower}%",),
            ).fetchall()
            for row in rows:
                results.append({
                    "type": "variable",
                    "name": row[0],
                    "lineno": row[1],
                    "col_offset": row[2],
                    "parent": row[3],
                    "file_path": row[4],
                })

        return results

    def close(self):
        """Close the database connection."""
        self.conn.close()
