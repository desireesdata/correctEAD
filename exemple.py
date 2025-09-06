from correctead import *

# Charger un fichier XML
# mon_document = load("ead/un_ir.xml")  # sans modifier l'encodage (possible, mais déconseillé)
mon_document = load("ead/un_ir.xml", encoding_override="utf-8") # Conseillé !
# Permet de se prémunir des problèmes d'encodage de Gaïa
mon_document.repair_mojibake("latin1_to_utf8")  

# Lire des valeurs avec XPath
print(mon_document.get("//archdesc/@level", as_text=True))
print(mon_document.get_doctype())

# Attributs
print("Voici les attributs de mon noeud archdesc:", 
      mon_document.get_attributes("//archdesc"))
print("Voici le contenu de @level de archdesc", 
      mon_document.get_attribut("archdesc", "level"))

# Modifications sur un attribut
if mon_document.get_attribut("archdesc", "level") == "fonds":
    mon_document.set_attribut("archdesc", "level", "recordgrp")

mon_document.set_attribut("origination","authfilenumber", "42")

# Vérifier la présence de la balise <testons>
# Et ajout noeud
if not mon_document.xpath("//testons"):
    print("Pas de balise testons existante")
    mon_document.add(
        "testons",
        "Victor Hugo",
        attrs={"authfilenumber": "BnF10293"},
        parent_xpath="//archdesc/did"  # parent par défaut ; à adapter si besoin
    )

# Poser un DOCTYPE EAD 2002 (par exemple)
mon_document.set_doctype(
    '<!DOCTYPE ead PUBLIC '
    '"//ISBN 1-931666-00-8//DTD ead.dtd (Encoded Archival Description (EAD) Version 2002)//EN" '
    '"/gaia/normes/ead.dtd">'
)

# Modification noeud textuel
mon_document.set("//publicationstmt/date", "Juillet 2026")

sujets = mon_document.nodes("subject")  # -> [EADNode, EADNode, ...]
if sujets:
    print("sujets :", sujets[0].text())  # méthode .text()

# Parcourir, lire/eécrirte texte et attributs
for s in mon_document.nodes("//controlaccess/subject"):
    print("avant :", s.text(), s.attrs())
    s.set_text(s.text().strip().capitalize())
    s.set_attr("encodinganalog", "610")

# supprimer un sujet vide :
for s in mon_document.nodes("subject"):
    if not s.text().strip():
        s.delete()

# récupérer tous les texte d'un coup:
print("Récup tous les textes d'un coup : ", mon_document.node_texts("//origination | //subject"))

# Supprimer les <acqinfo> dont le texte est exactement "Carton"
# for noeud in mon_document.get_nodes("acqinfo"):
#     if (noeud.text or "").strip() == "Carton":
#         mon_document.delete_node(noeud)

# Supprimer un noeud physdesc + ses enfant, s'ily a le mot carton (insensible à la casse)
for node in mon_document.nodes("//physdesc"):
    if node.text(deep=True).contains("carton"):
        node.delete()


# remplace TOUS les <subject> par <genreform>
for e in mon_document.get_nodes("//controlaccess/subject"):
    e.tag = "genreform"

# Déclaration XML
# mon_document.set_prelude('<?xml version="1.0" encoding="utf-8"?>')
mon_document.set_output_encoding("utf-8")
mon_document.save("ead/un_ir_transforme.xml")
