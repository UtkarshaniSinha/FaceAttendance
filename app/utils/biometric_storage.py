"""Private local storage for accepted enrolment image bytes."""

from __future__ import annotations

import secrets
import time
from pathlib import Path

# Windows: antivirus scanners and the search indexer briefly open newly
# written files, and deleting during that moment fails with WinError 32
# ("being used by another process"). Retry for about 1.5 s in total.
DELETE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)


class BiometricDeletionError(OSError):
    """A stored image could not be deleted (message contains no file path)."""


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

    def _path(self, storage_name: str) -> Path:
        target = (self.root / Path(storage_name).name).resolve()
        if target.parent != self.root:
            raise ValueError("Unsafe storage path.")
        return target

    def read(self, storage_name: str) -> bytes:
        """Read one stored image (only by its bare random name)."""

        return self._path(storage_name).read_bytes()

    def delete(self, storage_name: str) -> None:
        target = self._path(storage_name)
        for delay in (*DELETE_RETRY_DELAYS, None):
            try:
                target.unlink(missing_ok=True)
                return
            except PermissionError as error:
                if delay is None:
                    raise BiometricDeletionError(
                        "A stored face image is in use by another program and could not be deleted."
                    ) from error
                time.sleep(delay)
