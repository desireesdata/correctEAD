import unittest
import os
from correctead import load
from lxml import etree

class TestDocumentFeatures(unittest.TestCase):

    def setUp(self):
        """This method is called before each test."""
        repetition_fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'un_ir_repetition.xml')
        self.doc = load(repetition_fixture_path)

    def test_distribute_repetition_delete_node_with_comments(self):
        """Tests the 'delete_node' behavior with comments enabled."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="delete_node",
            add_comments=True
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]
        
        # Check parent comment
        parent_unittitle_element = modified_parent.xpath("did/unittitle")[0].element
        parent_comment = parent_unittitle_element.getnext()
        self.assertIsInstance(parent_comment, etree._Comment)
        self.assertIn("distribution de 'Encore un titre répétitif'", parent_comment.text)

        # Check child comment and node deletion
        first_child_did = modified_parent.children("c02")[0].xpath("did")[0].element
        # Find the comment by iterating through the children of the <did> element
        child_comment = None
        for child in first_child_did:
            if isinstance(child, etree._Comment):
                child_comment = child
                break
        self.assertIsNotNone(child_comment, "Comment should have been added to the child's parent")
        self.assertIn("comportement 'delete_node' appliqué", child_comment.text)
        
        child_unittitle = modified_parent.children("c02")[0].xpath("did/unittitle")
        self.assertEqual(child_unittitle, [], "Child unittitle should be deleted")

    def test_distribute_repetition_replace_by_sibling_with_comments(self):
        """Tests the 'replace_by_sibling' behavior with comments enabled."""
        modifs = self.doc.distribute_repetition(
            parent_selector="//c01",
            child_tag="c02",
            target_selector="did/unittitle",
            child_behavior="replace_by_sibling",
            sibling_selector="../unitid",
            add_comments=True
        )
        self.assertEqual(modifs, 1)
        modified_parent = self.doc.nodes("//c01")[1]

        # Check parent comment
        parent_unittitle_element = modified_parent.xpath("did/unittitle")[0].element
        parent_comment = parent_unittitle_element.getnext()
        self.assertIsInstance(parent_comment, etree._Comment)

        # Check child comment and text replacement
        child_unittitle_element = modified_parent.children("c02")[0].xpath("did/unittitle")[0].element
        child_comment = child_unittitle_element.getprevious()
        self.assertIsInstance(child_comment, etree._Comment)
        self.assertIn("comportement 'replace_by_sibling' appliqué", child_comment.text)
        self.assertEqual(child_unittitle_element.text, "Item 4")


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
