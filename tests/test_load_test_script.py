from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import sys
import unittest


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "load_test.py"
_SPEC = importlib.util.spec_from_file_location("load_test_script", _SCRIPT_PATH)
assert _SPEC is not None
load_test_script = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = load_test_script
assert _SPEC.loader is not None
_SPEC.loader.exec_module(load_test_script)


class LoadTestScriptTest(unittest.TestCase):
    def test_percentile_interpolates_values(self) -> None:
        self.assertEqual(load_test_script.percentile([], 0.95), 0.0)
        self.assertEqual(load_test_script.percentile([10.0], 0.95), 10.0)
        self.assertEqual(load_test_script.percentile([10.0, 20.0, 30.0], 0.5), 20.0)
        self.assertEqual(load_test_script.percentile([10.0, 20.0], 0.5), 15.0)

    def test_load_questions_file_supports_text_and_jsonl(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questions.jsonl"
            path.write_text(
                (
                    "光猫红灯咋办\n"
                    '{"query":"标准地址不存在怎么办"}\n'
                    '{"question":"RAG是什么意思"}\n'
                ),
                encoding="utf-8",
            )

            questions = load_test_script._load_questions_file(path)

            self.assertEqual(
                questions,
                [
                    "光猫红灯咋办",
                    "标准地址不存在怎么办",
                    "RAG是什么意思",
                ],
            )


if __name__ == "__main__":
    unittest.main()
