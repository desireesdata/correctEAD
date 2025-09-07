import os
from correctead import load, CorrectEADError

# 1. Define file paths
# The input file is in the tests/fixtures directory
# INPUT_FILE = os.path.join('tests', 'fixtures', 'un_ir.xml')
INPUT_FILE = os.path.join('tests', 'fixtures', 'un_ir.xml')
OUTPUT_FILE = 'un_ir_normalized.xml'

print(f"Loading EAD file: {INPUT_FILE}")

# 2. Load the document
# We use a try...except block to handle potential loading errors.
# We also override the encoding to be sure, as recommended in the docs.
try:
    doc = load(INPUT_FILE, encoding_override='utf-8')
except FileNotFoundError:
    print(f"Error: Input file not found at {INPUT_FILE}")
    exit(1)
except Exception as e:
    print(f"An error occurred while loading the file: {e}")
    exit(1)

print("Document loaded successfully. Starting normalization...")

# Repair potential encoding issues (e.g., latin-1 in a file declared as utf-8)
doc.repair_mojibake()
print("- Repaired mojibake issues.")

# 3. Perform some normalization tasks

# Change the 'level' attribute of <archdesc> to 'recordgrp'
level_before = doc.get_attribut("//archdesc", "level")
doc.set_attribut("//archdesc", "level", "recordgrp")
level_after = doc.get_attribut("//archdesc", "level")
print(f"- Changed <archdesc> level from '{level_before}' to '{level_after}'.")

# Add a <processinginfo> element to describe the normalization
try:
    doc.add(
        tag="processinginfo",
        text="Normalized with correctEAD package.",
        attrs={"encodinganalog": "42"},
        parent_xpath="//archdesc/did"
    )
    print("- Added <processinginfo> element.")
except CorrectEADError as e:
    print(f"Could not add <processinginfo> element: {e}")

# Capitalize all <subject> text content
subjects = doc.nodes("//controlaccess/subject")
for s in subjects:
    original_text = s.text()
    s.set_text(original_text.strip().capitalize())
print(f"- Capitalized {len(subjects)} <subject> elements.")

# 4. Set output encoding and save
doc.set_output_encoding('utf-8')
doc.save(OUTPUT_FILE)

print(f"\nNormalization complete. Saved output to: {OUTPUT_FILE}")
