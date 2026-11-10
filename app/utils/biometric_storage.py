"""Private local storage for accepted enrolment image bytes."""

from __future__ import annotations

import secrets
from pathlib import Path


class BiometricStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, data: bytes, extension: str) -> str:
        if extension not in {"jpg", "png"}:
            raise ValueError("Unsupported image format.")
        name = f"{secrets.token_urlsafe(24)}.{extension}"
        target = (self.root / name).resolve()
        if target.parent != self.root:
            raise ValueError("Unsafe storage path.")
        target.write_bytes(data)
        return name

    def delete(self, storage_name: str) -> None:
        target = (self.root / Path(storage_name).name).resolve()
        if target.parent != self.root:
            raise ValueError("Unsafe storage path.")
        target.unlink(missing_ok=True)
