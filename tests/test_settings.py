import unittest
from unittest.mock import patch

from config.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_production_profile_is_read_from_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "LLM_BASE_URL": "https://provider.example/v1",
                "LLM_API_KEY": "placeholder",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.app_env, "production")
        self.assertEqual(settings.llm_base_url, "https://provider.example/v1")

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "APP_ENV"):
            Settings(app_env="staging-typo").validate()


if __name__ == "__main__":
    unittest.main()
