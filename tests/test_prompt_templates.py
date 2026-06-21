import importlib.util
from pathlib import Path
import unittest


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts" / "answer_generation"


class PromptTemplateFilesTest(unittest.TestCase):
    def test_answer_generation_prompt_files_are_externalized(self) -> None:
        expected_files = {
            "system.md",
            "user.md",
            "augmented_context.md",
            "augmented_tool_call.md",
            "augmented_source.md",
            "augmented_tool_calls_empty.md",
            "augmented_sources_empty.md",
            "context_truncation_suffix.md",
            "source_context_item.md",
        }

        self.assertTrue(PROMPT_DIR.is_dir(), "prompts/answer_generation must exist")
        self.assertEqual(
            expected_files,
            {path.name for path in PROMPT_DIR.glob("*.md")},
        )

    def test_answer_generation_prompt_files_keep_required_placeholders(self) -> None:
        system_path = PROMPT_DIR / "system.md"
        user_path = PROMPT_DIR / "user.md"
        augmented_context_path = PROMPT_DIR / "augmented_context.md"

        self.assertTrue(system_path.is_file(), "system.md must exist")
        self.assertTrue(user_path.is_file(), "user.md must exist")
        self.assertTrue(
            augmented_context_path.is_file(), "augmented_context.md must exist"
        )

        system_prompt = system_path.read_text(encoding="utf-8")
        user_prompt = user_path.read_text(encoding="utf-8")
        augmented_context = augmented_context_path.read_text(encoding="utf-8")
        truncation_suffix = (
            PROMPT_DIR / "context_truncation_suffix.md"
        ).read_text(encoding="utf-8")

        self.assertIn("装维业务知识问答助手", system_prompt)
        self.assertIn("{question}", user_prompt)
        self.assertIn("{context}", user_prompt)
        self.assertIn("{request_id}", augmented_context)
        self.assertIn("{tool_calls_block}", augmented_context)
        self.assertIn("{sources_block}", augmented_context)
        self.assertIn("上下文已截断", truncation_suffix)

    def test_prompt_templates_can_be_loaded_and_rendered(self) -> None:
        self.assertIsNotNone(
            importlib.util.find_spec("rag_app.prompt_templates"),
            "rag_app.prompt_templates must provide prompt loading helpers",
        )
        from rag_app.prompt_templates import load_prompt_template, render_prompt_template

        system_prompt = load_prompt_template("answer_generation/system.md")
        user_prompt = render_prompt_template(
            "answer_generation/user.md",
            question="光猫 LOS 红灯怎么处理？",
            context="检索上下文",
        )

        self.assertIn("装维业务知识问答助手", system_prompt)
        self.assertEqual(
            "用户原始问题：\n光猫 LOS 红灯怎么处理？\n\n增强上下文：\n检索上下文",
            user_prompt,
        )

    def test_docker_image_copies_prompt_templates(self) -> None:
        dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(
            encoding="utf-8"
        )

        self.assertIn("COPY prompts ./prompts", dockerfile)


if __name__ == "__main__":
    unittest.main()
