import json
import os
from typing import Any, Dict


class JsonStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.base_dir, f"{name}.json")

    def read(self, name: str, default: Any = None) -> Any:
        path = self._path(name)
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def write(self, name: str, data: Any) -> None:
        path = self._path(name)
        tmp = path + ".tmp"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
