import os
import xml.etree.ElementTree as ET
import re

def nettoyer_xml(chaine_xml):
    """Nettoie les sauts de ligne et espaces inutiles entre les balises."""
    chaine_xml = re.sub(r'>\s+<', '><', chaine_xml)
    chaine_xml = re.sub(r'\s+</', '</', chaine_xml)
    return chaine_xml

def supprimer_namespaces_recursif(elem):
    """Supprime récursivement les préfixes de namespace dans l'arbre XML."""
    if '}' in elem.tag:
        elem.tag = elem.tag.split('}', 1)[1]
    for child in elem:
        supprimer_namespaces_recursif(child)

def indent_xml(elem, level=0):
    """Ajoute une indentation récursive à un élément XML."""
    i = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def format_xml_sans_sauts(input_file, output_file):
    """Lit un fichier XML, supprime les namespaces, nettoie et reformate sans sauts de ligne superflus."""
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Le fichier {input_file} n'existe pas.")
    if not os.path.isfile(input_file):
        raise ValueError(f"{input_file} n'est pas un fichier valide.")

    with open(input_file, 'r', encoding='utf-8') as f:
        xml_string = f.read()

    xml_string = nettoyer_xml(xml_string)

    try:
        tree = ET.ElementTree(ET.fromstring(xml_string))
    except ET.ParseError as e:
        raise ValueError(f"Erreur de parsing XML : {e}")

    root = tree.getroot()
    supprimer_namespaces_recursif(root)
    indent_xml(root)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'wb') as f:
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        xml_str = b'<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
        f.write(xml_str)
