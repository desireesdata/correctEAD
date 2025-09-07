import unittest
import os
from correctead import load

class TestDocumentFeatures(unittest.TestCase):

    def setUp(self):
        """This method is called before each test."""
        repetition_fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'un_ir_repetition.xml')
        # We load a fresh document for each test to ensure they are independent
        self.doc = load(repetition_fixture_path)

    def test_distribute_repetition_preserve(self):
        """Tests the default behavior (preserve children)."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="preserve"
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]
        self.assertEqual(modified_parent.xpath("did/unittitle")[0].text(), "Une autre série : Encore un titre répétitif")
        # Check that child title is unchanged
        child_title = modified_parent.children("c02")[0].xpath("did/unittitle")[0]
        self.assertEqual(child_title.text(), "Encore un titre répétitif")

    def test_distribute_repetition_delete_node(self):
        """Tests the 'delete_node' behavior on children."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="delete_node"
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]
        # Check that child unittitle node is gone
        child_unittitle = modified_parent.children("c02")[0].xpath("did/unittitle")
        self.assertEqual(child_unittitle, [])

    def test_distribute_repetition_delete_text(self):
        """Tests the 'delete_text' behavior on children."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="delete_text"
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]
        # Check that child unittitle node exists but is empty
        child_unittitle = modified_parent.children("c02")[0].xpath("did/unittitle")[0]
        self.assertEqual(child_unittitle.text(), "")

    def test_distribute_repetition_replace_by_sibling(self):
        """Tests the 'replace_by_sibling' behavior on children."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="replace_by_sibling",
            sibling_selector="../unitid"  # Correction: c'est unitid, pas unitdate
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]
        # Check that child unittitle has been replaced by the unitdate
        child_unittitle = modified_parent.children("c02")[0].xpath("did/unittitle")[0]
        self.assertEqual(child_unittitle.text(), "Item 4")
        child2_unittitle = modified_parent.children("c02")[1].xpath("did/unittitle")[0]
        self.assertEqual(child2_unittitle.text(), "Item 5")


# You can keep the old test class or remove it, for now I'll keep it.
class TestDocumentLoading(unittest.TestCase):

    def setUp(self):
        self.fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'un_ir.xml')

    def test_load_document(self):
        """Test that a document can be loaded successfully."""
        doc = load(self.fixture_path)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.root.tag, 'ead')

if __name__ == '__main__':
    unittest.main()