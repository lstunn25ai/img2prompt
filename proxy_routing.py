from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProxyEndpoint:
    label: str
    url: str


def normalize_proxy_url(value: str | None) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    return raw_value if "://" in raw_value else f"http://{raw_value}"


def build_proxy_endpoints(primary_url: str | None, reserve_url: str | None) -> list[ProxyEndpoint]:
    endpoints = [
        ProxyEndpoint("Основной", normalize_proxy_url(primary_url)),
        ProxyEndpoint("Резервный", normalize_proxy_url(reserve_url)),
    ]
    return [endpoint for endpoint in endpoints if endpoint.url]


def next_proxy_index(current_index: int, endpoint_count: int) -> int:
    if endpoint_count < 2:
        raise ValueError("Для переключения нужны как минимум два шлюза")
    return (current_index + 1) % endpoint_count


def load_proxy_index(state_path: Path, endpoint_count: int) -> int:
    try:
        saved_index = int(state_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0
    return saved_index if 0 <= saved_index < endpoint_count else 0


def save_proxy_index(state_path: Path, proxy_index: int) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(str(proxy_index), encoding="utf-8")
