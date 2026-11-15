"""Registry ordering is a view, not a mutation or stored scenario action."""
import copy
import json
import unittest
from test_noble_status_ui import NobleStatusUI

class NobleOrderUI(NobleStatusUI):
    def test_order_tracks_current_influence_keeps_family_together_and_dead_last_without_saving(self):
        baseline = self.page.evaluate('window.gilneasApp.getData()')
        expected = self.page.evaluate('async()=>{const {orderNobles}=await import("./assets/js/noble-order.mjs");return orderNobles(window.gilneasApp.getData()).map(n=>n.id);}')
        self.page.locator('#filter-nobles').click()
        self.assertEqual(self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)'), expected)
        self.assertEqual(expected[0], 'noble-genn')
        self.assertEqual(expected[-1], 'noble-archibald')
        before_json = json.dumps(baseline, ensure_ascii=False, indent=3) + '\n'
        self.page.evaluate('raw=>localStorage.setItem("gilneas-atlas-draft-v1",raw)', before_json)
        self.page.locator('#search').fill('Эшбери')
        self.assertEqual(self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)'), [id for id in expected if id in ['noble-ashbury','noble-ashbury-first']])
        self.page.locator('#search').fill('')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), baseline)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), before_json)
        self.assertEqual(self.errors, [])

    def test_native_kingdom_edit_reorders_families_after_save_and_reload_without_sorting_the_snapshot(self):
        baseline = self.page.evaluate('window.gilneasApp.getData()')
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.page.locator('#filter-nobles').click()
        initial_ids = self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)')
        self.assertEqual(initial_ids[:4], ['noble-genn','noble-mia','noble-tess','noble-liam'])
        self.page.locator('#editor-open').click()
        self.page.locator('label:has(#editing-enabled)').click()
        self.page.locator('[data-close="editor"]').click()
        self.page.locator('#council-open').click()
        self.page.locator('#royal-council [data-council-edit="council-noble-genn"]').click()
        self.page.locator('#council-person-kingdom-influence').fill('10')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), baseline)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.page.locator('#council-save').click()
        self.assertTrue(self.page.locator('#council-form').is_hidden())
        expected = copy.deepcopy(baseline)
        next(member for member in expected['royalCouncil']['members'] if member.get('refId')=='noble-genn')['influence']['kingdom'] = 10
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), expected)
        saved_raw = self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        self.assertEqual(json.loads(saved_raw), expected)
        self.page.keyboard.press('Escape')
        reordered = self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)')
        self.assertNotEqual(reordered, initial_ids)
        self.assertEqual(reordered[:2], ['noble-darius','noble-lorna'])
        self.assertEqual(reordered[-1], 'noble-archibald')
        first_royal = reordered.index('noble-mia')
        self.assertEqual(reordered[first_royal:first_royal+4], ['noble-mia','noble-genn','noble-tess','noble-liam'])
        self.assertEqual([noble['id'] for noble in expected['nobles']], [noble['id'] for noble in baseline['nobles']])
        self.assertEqual(expected['royalCouncil']['influence'], baseline['royalCouncil']['influence'])
        self.page.locator('#search').fill('Седогрив')
        matching = {noble['id'] for noble in baseline['nobles'] if 'седогрив' in noble['name'].casefold()}
        self.assertEqual(self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)'), [identifier for identifier in reordered if identifier in matching])
        self.page.locator('#search').fill('')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), expected)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), saved_raw)
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.locator('#filter-nobles').click()
        self.assertEqual(self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(node=>node.dataset.nobleId)'), reordered)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), expected)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), saved_raw)
        self.assertEqual(self.errors, [])

if __name__ == '__main__': unittest.main()
