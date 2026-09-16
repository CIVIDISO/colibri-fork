"""Small durable memory store owned by the standalone Colibri workbench."""

import json
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, root):
        self.path = Path(root) / "memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return value if isinstance(value, list) else []

    def list(self, project=None, limit=100):
        rows = self._read()
        if project:
            rows = [row for row in rows if row.get("project") == project]
        return rows[-max(1, min(limit, 500)):]

    def add(self, project, kind, content, source="operator"):
        content = str(content).strip()
        if not content:
            raise ValueError("memory content is required")
        rows = self._read()
        row = {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "project": str(project),
            "kind": str(kind or "note"),
            "source": str(source or "operator"),
            "content": content,
        }
        rows.append(row)
        self.path.write_text(json.dumps(rows[-2000:], indent=2) + "\n", encoding="utf-8")
        return row
