"""CSV export tool — parses JSON data and writes a CSV file."""

from __future__ import annotations

import csv
import io
import json
import os
import time

from langchain_core.tools import tool


def make_export_csv_tool(output_dir: str = "/tmp/exports") -> callable:
    """Create a tool that exports JSON data as a CSV file.

    Parameters
    ----------
    output_dir : str
        Directory where CSV files are saved.
    """

    @tool
    async def export_csv(data: str, filename: str) -> str:
        """Export JSON data as a CSV file.

        Use this after scraping or analyzing data to produce a downloadable
        report.

        Args:
            data: A JSON string — either a list of objects (each becomes a
                  row) or an object with a ``rows`` key containing the list.
            filename: Base name for the CSV file (no extension).

        Returns the file path of the saved CSV.
        """
        parsed = json.loads(data)

        # Accept both [{"a":1}, ...] and {"rows": [...]}
        if isinstance(parsed, dict) and "rows" in parsed:
            rows = parsed["rows"]
        elif isinstance(parsed, list):
            rows = parsed
        else:
            return "Error: data must be a JSON array or an object with a 'rows' key."

        if not rows:
            return "Error: no rows to export."

        os.makedirs(output_dir, exist_ok=True)
        ts = int(time.time())
        filepath = os.path.join(output_dir, f"{filename}_{ts}.csv")

        headers = list(rows[0].keys())
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return f"CSV exported to {filepath} ({len(rows)} rows)"

    return export_csv
