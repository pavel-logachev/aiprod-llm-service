import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class StreamlitAppTest(unittest.TestCase):
    def test_app_renders_required_controls(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run()

        self.assertFalse(app.exception)
        self.assertEqual(len(app.text_area), 1)
        self.assertEqual(len(app.selectbox), 2)
        self.assertEqual(len(app.button), 1)
        self.assertEqual(app.button[0].label, "Сгенерировать список покупок")

    def test_empty_submission_shows_safe_message(self) -> None:
        app = AppTest.from_file(str(APP_PATH)).run()

        app.button[0].click().run()

        self.assertFalse(app.exception)
        self.assertEqual(app.error[0].value, "Напишите, что хотите приготовить.")


if __name__ == "__main__":
    unittest.main()
