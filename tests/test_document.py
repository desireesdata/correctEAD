import unittest
import os
from correctead import load

class TestDocument(unittest.TestCase):

    def setUp(self):
        # Construct the path to the test fixture
        self.fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'un_ir.xml')

    def test_load_document(self):
        """Test that a document can be loaded successfully."""
        doc = load(self.fixture_path)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.root.tag, 'ead')

if __name__ == '__main__':
    unittest.main()
