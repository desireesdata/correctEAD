import correctead as ead
import io
from lxml import etree # On l'importe pour un affichage plus joli

# 1. On définit les données XML directement dans le script
#    pour avoir un exemple autonome.
xml_data = """
<ead>
    <archdesc level="fonds" type="inventory">
        <did>
            <unittitle>Test de distribution</unittitle>
        </did>
        <dsc>
            <c level="recordgrp">
                <did>
                    <unittitle>Registre paroissiaux</unittitle>
                    <unitdate>1600 - 1789</unitdate>
                </did>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1600-1650</unitdate>
                    </did>
                </c>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1650-1700</unitdate>
                    </did>
                </c>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1700-1789</unitdate>
                    </did>
                </c>
            </c>
            <c level="recordgrp">
                <did>
                    <unittitle>Registres paroissiaux</unittitle>
                    <unitdate>1789 - 200</unitdate>
                </did>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1600-1650</unitdate>
                    </did>
                </c>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1650-1700</unitdate>
                    </did>
                </c>
                <c level="file">
                    <did>
                        <unittitle>Baptêmes, mariages, sépultures</unittitle>
                        <unitdate>1700-1789</unitdate>
                    </did>
                </c>
            </c>
        </dsc>
    </archdesc>
</ead>
"""

# On charge le XML depuis notre chaîne de caractères
doc = ead.load(io.BytesIO(xml_data.encode('utf-8')))
output_file = "distribution_corrige.xml"

# 2. On affiche l'état AVANT la modification
parent_avant = doc.first_node("//c[@level='recordgrp']")
print(etree.tostring(parent_avant.element, pretty_print=True, encoding='unicode'))


# 3. On appelle la fonction avec les bons paramètres, en activant les commentaires
print("\n--- LANCEMENT DE distribute_repetition() AVEC add_comments=True ---")
modifs = doc.distribute_repetition(
    parent_selector="//c[@level='recordgrp']",
    child_tag="c",
    target_selector="did/unittitle",
    child_behavior="delete_node",  # On supprime les noeuds enfants pour bien voir les commentaires
    sibling_selector="../unitdate",       # <-- On remplace... (This line is kept to maintain the structure, but its comment is now misleading)
    add_comments=True               # <-- On active l'ajout de commentaires
)
print(f"-> {modifs} parent(s) ont été modifiés.")


# 4. On affiche l'état APRÈS la modification et on sauvegarde
if modifs > 0:
    print("\n--- APRÈS TRAITEMENT ---")
    parent_apres = doc.first_node("//c[@level='recordgrp']")
    print(etree.tostring(parent_apres.element, pretty_print=True, encoding='unicode'))
    
    doc.save(output_file)
    print(f"\nFichier de sortie enregistré : {output_file}")
else:
    print("\nAucune modification n'a été appliquée.")