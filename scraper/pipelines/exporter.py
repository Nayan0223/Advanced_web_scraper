"""Multi-format data exporter supporting JSON, JSONL, CSV, and SQLite."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel


class DataExporter:
    """Exports scraped items to multiple storage and data exchange formats."""

    @staticmethod
    def _to_dict_list(items: List[Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, BaseModel):
                result.append(item.model_dump(mode="json"))
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append({"value": item})
        return result

    @classmethod
    def export(
        cls,
        items: List[Any],
        output_path: Union[str, Path],
        file_format: Optional[Literal["json", "jsonl", "csv", "sqlite"]] = None,
        sqlite_table: str = "scraped_data",
    ) -> Path:
        """Export list of items into target file based on format or file extension."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if file_format is None:
            ext = path.suffix.lower().lstrip(".")
            if ext in {"json", "jsonl", "csv", "sqlite", "db"}:
                file_format = "sqlite" if ext in {"sqlite", "db"} else ext  # type: ignore
            else:
                file_format = "json"

        dict_items = cls._to_dict_list(items)

        if file_format == "json":
            cls.to_json(dict_items, path)
        elif file_format == "jsonl":
            cls.to_jsonl(dict_items, path)
        elif file_format == "csv":
            cls.to_csv(dict_items, path)
        elif file_format == "sqlite":
            cls.to_sqlite(dict_items, path, table_name=sqlite_table)
        else:
            raise ValueError(f"Unsupported export format: {file_format}")

        return path

    @staticmethod
    def to_json(items: List[Dict[str, Any]], path: Path) -> None:
        """Export items as pretty formatted JSON."""
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2, default=str)
            f.write("\n")

    @staticmethod
    def to_jsonl(items: List[Dict[str, Any]], path: Path) -> None:
        """Export items as newline-delimited JSON (JSONL)."""
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def to_csv(items: List[Dict[str, Any]], path: Path) -> None:
        """Export items to CSV with nested structures serialized as JSON."""
        if not items:
            path.write_text("", encoding="utf-8")
            return

        # Determine all unique fieldnames
        fieldnames: List[str] = []
        for item in items:
            for key in item.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                row = {}
                for key in fieldnames:
                    val = item.get(key, "")
                    if isinstance(val, (dict, list)):
                        row[key] = json.dumps(val, ensure_ascii=False, default=str)
                    else:
                        row[key] = val
                writer.writerow(row)

    @staticmethod
    def to_sqlite(items: List[Dict[str, Any]], path: Path, table_name: str = "scraped_data") -> None:
        """Export items directly into a SQLite database table."""
        if not items:
            return

        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Collect columns
        columns = list({k: True for item in items for k in item.keys()}.keys())

        # Create table with dynamic TEXT/REAL/INTEGER columns
        col_defs = []
        for col in columns:
            safe_col = f'"{col}"'
            col_defs.append(f"{safe_col} TEXT")

        create_stmt = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)});'
        cursor.execute(create_stmt)

        # Insert rows
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join([f'"{c}"' for c in columns])
        insert_stmt = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

        for item in items:
            values = []
            for col in columns:
                v = item.get(col)
                if isinstance(v, (dict, list)):
                    values.append(json.dumps(v, default=str))
                else:
                    values.append(str(v) if v is not None else None)
            cursor.execute(insert_stmt, values)

        conn.commit()
        conn.close()
