from correctead import *

# ******** Conversion en utf-8 ********
mon_document = load("ead/un_ir.xml", encoding_override="utf-8")
n = mon_document.repair_mojibake("latin1_to_utf8")
print("textes corrigés:", n)

print("in:", mon_document.get_input_encoding())  # doit afficher: utf-8
mon_document.set_output_encoding("utf-8")
mon_document.save("ead/un_ir_modifie.xml")

# ***** Préservation du format d'encodage de l'input ********
# si la déclaration ISO-8859-1 est correcte :
mon_document = load("ead/un_ir.xml") 
print("in:", mon_document.get_input_encoding())

mon_document.set_output_encoding("preserve")
mon_document.save("ead/un_ir_preserve.xml")
