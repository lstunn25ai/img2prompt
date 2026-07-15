import tempfile
import unittest
from pathlib import Path

from proxy_routing import (
    ProxyEndpoint,
    build_proxy_endpoints,
    load_proxy_index,
    next_proxy_index,
    save_proxy_index,
)


class ProxyRoutingTests(unittest.TestCase):
    def test_builds_primary_and_reserve_endpoints_without_exposing_urls(self):
        endpoints = build_proxy_endpoints(
            primary_url="primary-gateway:8080",
            reserve_url="http://reserve-gateway:8080",
        )

        self.assertEqual(
            [
                ProxyEndpoint(label="Основной", url="http://primary-gateway:8080"),
                ProxyEndpoint(label="Резервный", url="http://reserve-gateway:8080"),
            ],
            endpoints,
        )

    def test_skips_empty_reserve_endpoint(self):
        endpoints = build_proxy_endpoints("http://primary-gateway:8080", "")

        self.assertEqual([ProxyEndpoint("Основной", "http://primary-gateway:8080")], endpoints)

    def test_next_proxy_index_cycles_between_two_endpoints(self):
        self.assertEqual(1, next_proxy_index(0, endpoint_count=2))
        self.assertEqual(0, next_proxy_index(1, endpoint_count=2))

    def test_persists_valid_index_and_falls_back_for_invalid_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "proxy-state"
            save_proxy_index(state_path, 1)
            self.assertEqual(1, load_proxy_index(state_path, endpoint_count=2))

            state_path.write_text("99", encoding="utf-8")
            self.assertEqual(0, load_proxy_index(state_path, endpoint_count=2))


if __name__ == "__main__":
    unittest.main()
