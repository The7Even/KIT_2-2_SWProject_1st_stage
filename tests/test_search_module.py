import unittest

from src.region_code_client import RegionCodeApiError, RegionCodeClient
from src.search_module import SearchModule


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.request = None

    def get(self, url, params, timeout):
        self.request = (url, params, timeout)
        return self.response


class SearchModuleTests(unittest.TestCase):
    def test_search_by_title_and_location(self):
        module = SearchModule()

        self.assertEqual(len(module.search_act("\ub3c4\uc2dc")), 1)
        self.assertEqual(len(module.search_act("OO\uc2dc")), 1)
        self.assertEqual(module.search_act("\uc5c6\ub294 \ud65c\ub3d9"), [])

    def test_search_by_region_code(self):
        module = SearchModule()

        results = module.search_act(region_code="4711311800")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["region_code"], "4711311800")

    def test_search_by_region_uses_resolver(self):
        calls = []

        def resolver(region_name):
            calls.append(region_name)
            return [{"code": "4711311800", "name": "\uad6c\ubbf8\uc2dc"}]

        module = SearchModule(region_resolver=resolver)

        self.assertEqual(len(module.search_by_region("\uad6c\ubbf8")), 1)
        self.assertEqual(calls, ["\uad6c\ubbf8"])

    def test_invalid_search_inputs_return_empty_list(self):
        module = SearchModule()

        self.assertEqual(module.search_act(None), [])
        self.assertEqual(module.search_act(region_code=123), [])
        self.assertEqual(module.search_by_region(""), [])


class RegionCodeClientTests(unittest.TestCase):
    def test_api_response_is_mapped_to_internal_shape(self):
        session = FakeSession(
            FakeResponse({"data": [{"admCode": 4711311800, "admName": "\uad6c\ubbf8\uc2dc"}]})
        )
        client = RegionCodeClient(
            base_url="https://example.test/regions",
            session=session,
        )
        client.code_field = "admCode"
        client.name_field = "admName"

        self.assertEqual(
            client.find_regions("\uad6c\ubbf8"),
            [{"code": "4711311800", "name": "\uad6c\ubbf8\uc2dc"}],
        )
        self.assertEqual(
            session.request,
            (
                "https://example.test/regions",
                {"query": "\uad6c\ubbf8"},
                5.0,
            ),
        )

    def test_missing_api_url_is_reported(self):
        client = RegionCodeClient(base_url=None)

        with self.assertRaises(RegionCodeApiError):
            client.find_regions("\uad6c\ubbf8")


if __name__ == "__main__":
    unittest.main()
