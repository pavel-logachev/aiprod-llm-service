import unittest

from cache.ttl_cache import TTLCache, build_cache_key


class TTLCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_value_expires_after_ttl(self) -> None:
        now = [100.0]
        cache = TTLCache(10, clock=lambda: now[0])

        await cache.set("key", "value")
        self.assertEqual(await cache.get("key"), "value")

        now[0] = 110.0
        self.assertIsNone(await cache.get("key"))

    def test_key_contains_all_semantic_parameters(self) -> None:
        base = build_cache_key(
            message="hello",
            model="model-a",
            temperature=0.2,
            system_prompt="system",
        )
        variants = {
            build_cache_key(
                message="other",
                model="model-a",
                temperature=0.2,
                system_prompt="system",
            ),
            build_cache_key(
                message="hello",
                model="model-b",
                temperature=0.2,
                system_prompt="system",
            ),
            build_cache_key(
                message="hello",
                model="model-a",
                temperature=0.8,
                system_prompt="system",
            ),
            build_cache_key(
                message="hello",
                model="model-a",
                temperature=0.2,
                system_prompt="different",
            ),
        }
        self.assertNotIn(base, variants)


if __name__ == "__main__":
    unittest.main()

