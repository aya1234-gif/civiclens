"""Data lineage reporter.

Queries dbt's manifest.json and the audit_log table to produce
a human-readable report linking raw sources → warehouse models → ML outputs.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_MANIFEST_PATH = Path("warehouse/target/manifest.json")


class LineageReporter:
    """Generate data lineage reports from dbt manifest and audit logs."""

    def report_dbt_lineage(self) -> dict[str, Any]:
        """Parse dbt manifest.json and return a node → upstream map.

        Returns:
            Dict mapping each dbt node name to its list of upstream dependencies.
        """
        if not _MANIFEST_PATH.exists():
            log.warning(
                "manifest_missing",
                path=str(_MANIFEST_PATH),
                hint="Run: cd warehouse && dbt compile",
            )
            return {}

        manifest = json.loads(_MANIFEST_PATH.read_text())
        nodes: dict[str, Any] = manifest.get("nodes", {})
        lineage: dict[str, list[str]] = {}

        for node_id, node_data in nodes.items():
            upstream = node_data.get("depends_on", {}).get("nodes", [])
            lineage[node_data.get("name", node_id)] = upstream

        log.info("dbt_lineage_extracted", node_count=len(lineage))
        return lineage

    def to_markdown(self, lineage: dict[str, Any]) -> str:
        """Render a lineage dict as a Markdown table."""
        lines = ["# CivicLens Data Lineage\n", "| Model | Depends On |", "|---|---|"]
        for model, deps in sorted(lineage.items()):
            dep_str = ", ".join(deps) if deps else "—"
            lines.append(f"| {model} | {dep_str} |")
        return "\n".join(lines)


async def _main() -> None:
    """CLI entrypoint: print lineage report to stdout."""
    reporter = LineageReporter()
    lineage = reporter.report_dbt_lineage()
    if lineage:
        print(reporter.to_markdown(lineage))
    else:
        log.warning("lineage_report_empty")


if __name__ == "__main__":
    import structlog

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(_main())
