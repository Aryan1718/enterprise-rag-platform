from __future__ import annotations

from pathlib import Path


def _resolve_shared_paths() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    paths: list[str] = []

    local_server_app = root.parent / "server" / "app"
    if local_server_app.exists():
        paths.append(str(local_server_app))

    docker_shared = root / "shared"
    if docker_shared.exists():
        paths.append(str(docker_shared))

    return paths


__path__ = _resolve_shared_paths()
