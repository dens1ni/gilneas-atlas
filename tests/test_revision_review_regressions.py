"""Native snapshot/import regressions for the bounded publication review fixes."""
import functools
import http.server
import json
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DRAFT_KEY = "gilneas-atlas-draft-v1"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class RevisionReviewRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT))
        )
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(f"http://127.0.0.1:{self.server.server_port}/")
        self.page.wait_for_function("window.gilneasApp?.ready")

    def tearDown(self):
        self.context.close()

    def stored(self):
        return self.page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")

    def test_invalid_noble_name_native_import_leaves_live_and_exact_storage_unchanged(self):
        self.page.evaluate("window.gilneasApp.replaceData(window.gilneasApp.getData())")
        before = self.page.evaluate("window.gilneasApp.getData()")
        raw = json.dumps(before, ensure_ascii=False, indent=3) + "\n"
        self.page.evaluate("raw => localStorage.setItem('gilneas-atlas-draft-v1', raw)", raw)
        self.page.locator("#editor-open").click()
        for value in ["", " \t\n ", None, {}, [], 42, False]:
            with self.subTest(name=value):
                bad = json.loads(json.dumps(before))
                bad["nobles"][0]["name"] = value
                self.page.locator("#import-json").set_input_files({
                    "name": "invalid-noble.json", "mimeType": "application/json",
                    "buffer": json.dumps(bad, ensure_ascii=False).encode("utf-8"),
                })
                self.page.wait_for_function("!document.getElementById('import-json').disabled && document.getElementById('import-json').value === ''")
                self.assertRegex(self.page.locator("#editor-error").text_content(), r"имя.*знат|имя.*персонаж|noble.*name")
                self.assertEqual(self.page.evaluate("window.gilneasApp.getData()"), before)
                self.assertEqual(self.stored(), raw)
        self.assertFalse(self.errors, self.errors)

    def test_invalid_noble_house_native_import_leaves_live_and_exact_storage_unchanged(self):
        self.page.evaluate("window.gilneasApp.replaceData(window.gilneasApp.getData())")
        before = self.page.evaluate("window.gilneasApp.getData()")
        raw = json.dumps(before, ensure_ascii=False, indent=3) + "\n"
        self.page.evaluate("raw => localStorage.setItem('gilneas-atlas-draft-v1', raw)", raw)
        self.page.locator("#editor-open").click()
        for value in ["missing-house", 1, "", {}, [], False]:
            with self.subTest(house=value):
                bad = json.loads(json.dumps(before))
                bad["nobles"][0]["house"] = value
                self.page.locator("#import-json").set_input_files({
                    "name": "invalid-noble.json", "mimeType": "application/json",
                    "buffer": json.dumps(bad, ensure_ascii=False).encode("utf-8"),
                })
                self.page.wait_for_function("!document.getElementById('import-json').disabled && document.getElementById('import-json').value === ''")
                self.assertRegex(self.page.locator("#editor-error").text_content(), r"фракция.*персонаж|дом.*персонаж|noble.*house")
                self.assertEqual(self.page.evaluate("window.gilneasApp.getData()"), before)
                self.assertEqual(self.stored(), raw)
        self.assertFalse(self.errors, self.errors)

    def test_invalid_noble_dossier_text_native_import_leaves_live_and_exact_storage_unchanged(self):
        self.page.evaluate("window.gilneasApp.replaceData(window.gilneasApp.getData())")
        before = self.page.evaluate("window.gilneasApp.getData()")
        raw = json.dumps(before, ensure_ascii=False, indent=3) + "\n"
        self.page.evaluate("raw => localStorage.setItem('gilneas-atlas-draft-v1', raw)", raw)
        self.page.locator("#editor-open").click()
        fields = ["title", "description", "appearance", "socialStatus", "overlordText", "allegiance", "holdingsNote", "wowpediaUrl"]
        for field, value in [(field, {}) for field in fields] + [("appearance", None)]:
            with self.subTest(field=field, value=value):
                bad = json.loads(json.dumps(before))
                bad["nobles"][0][field] = value
                self.page.locator("#import-json").set_input_files({
                    "name": "invalid-noble.json", "mimeType": "application/json",
                    "buffer": json.dumps(bad, ensure_ascii=False).encode("utf-8"),
                })
                self.page.wait_for_function("!document.getElementById('import-json').disabled && document.getElementById('import-json').value === ''")
                self.assertIn("поле персонажа: " + field, self.page.locator("#editor-error").text_content())
                self.assertEqual(self.page.evaluate("window.gilneasApp.getData()"), before)
                self.assertEqual(self.stored(), raw)
        self.assertFalse(self.errors, self.errors)

    def test_valid_migration_preserves_custom_objects_positions_and_deleted_sources(self):
        draft = self.page.evaluate("window.gilneasApp.getData()")
        draft["meta"]["publicationRevision"] = "review-legacy-revision"
        draft["meta"]["gilneasCrest"] = "https://example.invalid/author-crest.svg"
        draft["meta"]["wallConstruction"] = {"value": 43, "max": 91, "note": "  Author stage  "}
        draft["sources"] = [source for source in draft["sources"] if source["id"] != 1]
        def remove_deleted_references(value):
            if isinstance(value, list):
                for child in value:
                    remove_deleted_references(child)
            elif isinstance(value, dict):
                for key, child in value.items():
                    if key == "sources" and isinstance(child, list):
                        value[key] = [source_id for source_id in child if source_id != 1]
                    else:
                        remove_deleted_references(child)
        remove_deleted_references(draft)
        location = next(location for location in draft["locations"] if location["id"] == "gilneas-city")
        location["x"] += 12
        location["description"] = "  Author place description  "
        location["objects"].append({"id": "review-author-forge", "name": "  Авторская кузница  ", "type": "building", "owner": "", "description": "  Author text  ", "modifiers": [], "extra": {"literal": "<script>literal</script>"}})
        raw = json.dumps(draft, ensure_ascii=False, indent=3) + "\n"
        self.page.evaluate("raw => localStorage.setItem('gilneas-atlas-draft-v1', raw)", raw)
        self.page.reload()
        self.page.wait_for_function("window.gilneasApp?.ready")
        data = self.page.evaluate("window.gilneasApp.getData()")
        actual = next(record for record in data["locations"] if record["id"] == location["id"])
        self.assertEqual(actual, location)
        self.assertEqual(data["sources"], draft["sources"])
        for field in ["gilneasCrest", "wallConstruction"]:
            self.assertEqual(data["meta"][field], draft["meta"][field])
        self.assertNotEqual(data["meta"]["publicationRevision"], draft["meta"]["publicationRevision"])
        self.assertEqual(self.stored(), raw)
        self.assertFalse(self.errors, self.errors)

    def test_conflicting_new_source_keeps_exact_live_draft_without_load_time_write(self):
        draft = self.page.evaluate("window.gilneasApp.getData()")
        draft["meta"]["publicationRevision"] = "review-legacy-revision"
        draft["meta"]["gilneasCrest"] = "https://example.invalid/author-crest.svg"
        draft["meta"]["wallConstruction"] = {"value": 43, "max": 91, "note": "  Author stage  "}
        draft["nobles"][0]["description"] = "  Author biography, not release lore  "
        source = next(source for source in draft["sources"] if source["id"] == 65)
        source["url"] = "https://example.invalid/author-65"
        source["canonicalUrl"] = source["url"]
        source["title"] = "Author source 65"
        raw = json.dumps(draft, ensure_ascii=False, indent=3) + "\n"
        self.page.evaluate("raw => localStorage.setItem('gilneas-atlas-draft-v1', raw)", raw)
        self.context.add_init_script("""
            window.reviewStorageWrites = [];
            const original = Storage.prototype.setItem;
            Storage.prototype.setItem = function(key, value) {
                window.reviewStorageWrites.push([key, value]);
                return original.call(this, key, value);
            };
        """)
        warnings = []
        self.page.on("console", lambda message: warnings.append(message.text) if message.type == "warning" else None)
        self.page.reload()
        self.page.wait_for_function("window.gilneasApp?.ready")
        self.assertEqual(self.page.evaluate("window.gilneasApp.getData()"), draft)
        self.assertEqual(self.stored(), raw)
        self.assertEqual(self.page.evaluate("window.reviewStorageWrites"), [])
        self.assertTrue(any("Source-ID conflict" in warning and "65" in warning for warning in warnings), warnings)
        self.assertFalse(self.errors, self.errors)


if __name__ == "__main__":
    unittest.main()
