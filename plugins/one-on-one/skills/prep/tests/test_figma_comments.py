import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import figma_comments  # noqa: E402


class FileKey(unittest.TestCase):
    def test_design_url_with_node(self):
        self.assertEqual(figma_comments.file_key("https://www.figma.com/design/AbC123/ICBR?node-id=1-2"), "AbC123")

    def test_legacy_file_url(self):
        self.assertEqual(figma_comments.file_key("https://www.figma.com/file/Zz9/Old-name"), "Zz9")

    def test_branch_url_uses_main_file(self):
        self.assertEqual(figma_comments.file_key("https://www.figma.com/design/Main1/x/branch/Br2/y"), "Main1")

    def test_bare_key(self):
        self.assertEqual(figma_comments.file_key("AbC123"), "AbC123")

    def test_rejects_other_urls(self):
        with self.assertRaises(SystemExit):
            figma_comments.file_key("https://example.com/design/x")


if __name__ == "__main__":
    unittest.main()
