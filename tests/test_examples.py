import unittest
import os
import shutil
from lxml import etree
from correctead import load

class TestExamples(unittest.TestCase):

    def setUp(self):
        self.base_path = os.path.dirname(__file__)
        self.fixtures_path = os.path.join(self.base_path, 'fixtures')
        self.output_path = os.path.join(self.base_path, 'output')
        # Create a temporary output directory
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

    def tearDown(self):
        # Remove the temporary output directory
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)

    def test_example_1_normalisation_simple(self):
        """Tests the main normalization example from the README."""
        # Define input and output paths
        input_file = os.path.join(self.fixtures_path, 'un_ir.xml')
        output_file = os.path.join(self.output_path, 'un_ir_transforme.xml')

        # 1. Load and repair
        doc = load(input_file, encoding_override="utf-8")
        # Assuming the fixture might have mojibake
        doc.repair_mojibake("latin1_to_utf8")

        # 2. Change attribute
        if doc.get_attribut("archdesc", "level") == "fonds":
            doc.set_attribut("archdesc", "level", "recordgrp")

        # 3. Add a new node
        if not doc.xpath("//testons"):
            doc.add("testons", "Victor Hugo",
                    attrs={"authfilenumber": "BnF10293"},
                    parent_xpath="//archdesc/did")

        # 4. Set DOCTYPE
        doc.set_doctype(
            '<!DOCTYPE ead PUBLIC "//ISBN 1-931666-00-8//DTD ead.dtd (Encoded Archival Description (EAD) Version 2002)//EN" "/gaia/normes/ead.dtd">'
        )

        # 5. Set text content
        doc.set("//publicationstmt/date", "Juillet 2026")

        # 6. Modify nodes with the EADNode API
        for s in doc.nodes("//controlaccess/subject"):
            s.set_text(s.text().strip().capitalize())
            s.set_attr("encodinganalog", "610")

        # 7. Use lxml-level access to rename tags
        # Note: The loop needs to be on a static list, as modifying the tag invalidates the iterator
        nodes_to_rename = list(doc.get_nodes("//controlaccess/subject"))
        for e in nodes_to_rename:
            e.tag = "genreform"

        # 8. Save the document
        doc.set_output_encoding("utf-8")
        doc.save(output_file)

        # 9. Verify the output
        self.assertTrue(os.path.exists(output_file))

        # Re-load the saved file to check its content
        result_doc = load(output_file)

        # Check attribute change
        self.assertEqual(result_doc.get_attribut("//archdesc", "level"), "recordgrp")

        # Check added node
        self.assertTrue(result_doc.xpath("//testons"))
        self.assertEqual(result_doc.get("//testons/text()", as_text=True)[0], "Victor Hugo")
        self.assertEqual(result_doc.get_attribut("//testons", "authfilenumber"), "BnF10293")

        # Check DOCTYPE
        self.assertIn("//ISBN 1-931666-00-8//DTD ead.dtd", result_doc.get_doctype())

        # Check set text
        self.assertEqual(result_doc.get("//publicationstmt/date/text()", as_text=True)[0], "Juillet 2026")

        # Check tag rename and modifications
        self.assertFalse(result_doc.xpath("//subject"), "<subject> tags should have been renamed")
        genreform_nodes = result_doc.nodes("//genreform")
        self.assertTrue(len(genreform_nodes) > 0, "<genreform> tags should be present")
        for node in genreform_nodes:
            self.assertEqual(node.get_attr("encodinganalog"), "610")
            # Check that text is capitalized
            self.assertEqual(node.text(), node.text().capitalize())

if __name__ == '__main__':
    unittest.main()
