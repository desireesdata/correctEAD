# correctEAD

Outil Python basique pour inspecter et transformer des fichiers XML EAD (Encoded Archival Description) dans le cadre de la normalisation des instruments de recherche, basé sur `lxml`. Il fournit des fonctions de lecture/écriture (XPath, attributs, insertion/suppression) pour réaliser des ajustements directement en Python, sans recourir à XSLT. Quant à l'utilisation directe de `lxml`, `correctead` peut sembler superflu, mais permet d'effectuer des actions explicites propres à la correction archivistique.

> Ce choix peut être également pertinent lorsque l’on souhaite éviter les écarts de comportement liés aux différences de versions de XSLT/processeurs; ou que l'on veut mettre en place une pipeline de traitement déclarative, sans appels imbriqués. L'utilisaiton via Python permet également de bénéficier d'autres fonctionnalités servies par l'écosystème Python (fuzzy search, appels d'API institutionnelles, etc.), sans recourir à des technologies diverses qui peuvent compliquer une chaîne de traitement pouvant inclure l'indexation de l'instrument de recherche.

Cependant, `correcEAD` ne permet pas d'effectuer des transformations complexes... à l'instar de XSLT. C'est un **outil de correction**.

`correctead` fournit une API simple pour :

* charger un XML en contrôlant précisément l’encodage ;
* corriger certains cas de *mojibake* (UTF-8 ↔︎ Latin-1) ;
* lire et modifier du contenu via XPath ;
* manipuler les attributs ;
* insérer/supprimer des nœuds ;
* préserver ou définir le prologue (déclaration XML, DOCTYPE) à l’enregistrement.
* distribuer une information répétée et partagée par les mêmes enfants en l'intégrant à l'élément parent (principe ISAD-G)

> Remarque : l’outil n’effectue pas de validation de schéma (DTD/Relax NG/Schéma XML) !

## Exemple simple 

```python
from correctead import load, CorrectEADError

# Gestion i/o fichiers
INPUT_FILE = 'un_ir.xml'
OUTPUT_FILE = 'un_ir_modif.xml'
doc = load(INPUT_FILE, encoding_override='utf-8')
doc.repair_mojibake()

# Manipulations simples de balises
print(doc.get("//archdesc/@level", as_text=True))
print(doc.get_doctype())
doc.set_doctype("<!DOCTYPE morbier>")

# Manipulation sur plusieurs balises
for node in doc.nodes("persname[not(@authfilenumber)]"):
    a = node.text()
    node.set_attr("authfilenumber", "42")
    print("Noms: ", a)

# Modification de balises
doc.set("//publisher", "Service d'archives fantaisiste")

# Ajout de balises
if doc.xpath("//did/origination/custodhist"):
    print("l'élément existe déjà !")
else : 
    try:
        doc.add(
            tag="custodhist",
            text="Historique de conservation : blabla",
            parent_xpath="//did/origination"
        )
        print("Element ajouté avec succès !")
    except CorrectEADError as e:
        print(":/")

doc.set_output_encoding('utf-8')
doc.save(OUTPUT_FILE)

```

---

## Installation

Le package peut être installé directement depuis GitHub via `pip`. Il est recommandé de le faire dans un environnement virtuel.

```bash
pip install git+https://github.com/desireesdata/correctEAD.git@package
```

La dépendance à `lxml` sera automatiquement installée.

L'importation se fait ensuite de manière ciblée :
```python
from correctead import load, EADNode
```

Compatibilité Python : 3.9+ recommandé.

---

## Principes

* Le chargement s’effectue avec `lxml.etree`. Par défaut, `resolve_entities=False` et `remove_blank_text=False`.
* Le DOCTYPE présent dans le fichier source est conservé tel quel (si présent).
* L’encodage d’entrée détecté/déclaré est mémorisé ; l’encodage de sortie est configurable (`preserve` ou explicite).
* La sérialisation finale réécrit un prologue propre (déclaration XML + DOCTYPE si défini) en **un seul encodage**. Les caractères non représentables sont sortis en références numériques (`errors="xmlcharrefreplace"`).

---

## Prise en main

### Chargement et encodage

```python
from correctead import load

# 1) Chargement en forçant l’encodage (recommandé pour contourner des déclarations erronées)
doc = load("chemin/vers/votre/fichier.xml", encoding_override="utf-8")

# 2) Correction heuristique de mojibake (Latin-1 mal décodé en UTF-8)
n = doc.repair_mojibake("latin1_to_utf8")
print("Textes corrigés :", n)

print("Encodage d'entrée détecté :", doc.get_input_encoding())  # ex. 'utf-8'
doc.set_output_encoding("utf-8")  # ou 'preserve' pour réutiliser l'encodage d'entrée

doc.save("chemin/vers/votre/fichier_sortie.xml")
```

#### Préservation de l’encodage d’origine

```python
doc = load("chemin/vers/votre/fichier.xml")   # utilise l’encodage déclaré par le fichier
doc.set_output_encoding("preserve")
doc.save("chemin/vers/votre/fichier_preserve.xml")
```

### DOCTYPE et déclaration XML

```python
# Récupération du DOCTYPE d'origine
print(doc.get_doctype())

# Définir un DOCTYPE (ex. EAD 2002)
doc.set_doctype(
    '<!DOCTYPE ead PUBLIC '
    '"//ISBN 1-931666-00-8//DTD ead.dtd (Encoded Archival Description (EAD) Version 2002)//EN" '
    '"/gaia/normes/ead.dtd">'
)

# (Optionnel) remplacer la déclaration XML d’entrée
# doc.set_prelude('<?xml version="1.0" encoding="utf-8"?>')
```

---

## Lecture

### XPath (valeurs et existence)

```python
# Valeurs (atomiques converties en str si as_text=True)
levels = doc.get("//archdesc/@level", as_text=True)
print(levels)

# Test d'existence
if doc.xpath("//testons"):
    print("<testons> présent")
```

### Attributs

```python
# Tous les attributs des <archdesc>
print(doc.get_attributes("//archdesc"))

# Une valeur d'attribut
level = doc.get_attribut("archdesc", "level")   # 1re occurrence
levels = doc.get_attribut("//archdesc", "level", many=True)  # liste alignée sur les nœuds
```

---

## Modification

### Attributs

```python
# Changer une valeur sur le premier archdesc
if doc.get_attribut("archdesc", "level") == "fonds":
    doc.set_attribut("archdesc", "level", "recordgrp")

# Définir un attribut sur toutes les balises <origination>
doc.set_attribut("origination", "authfilenumber", "42")

# Supprimer un attribut
doc.delete_attribut("//controlaccess/subject", "encodinganalog")

# Supprimer tous les attributs sauf 'id'
doc.delete_attributes("//physdesc", keep=["id"])
```

### Nœuds et contenu

```python
# Ajouter un nœud sous //archdesc/did (parent par défaut)
doc.add(
    "testons",
    "Victor Hugo",
    attrs={"authfilenumber": "BnF10293"},
    parent_xpath="//archdesc/did"
)

# Écrire un texte à un emplacement (création automatique simple de chemin //a/b/c)
doc.set("//publicationstmt/date", "Juillet 2026")
```

> Création automatique : uniquement pour des chemins simples de type `//a/b/c` (pas de prédicats, namespaces complexes, etc.).

### Nettoyage et Transformations Globales

Ces méthodes permettent d'appliquer des transformations sur l'ensemble du document.

```python
# Supprimer tous les namespaces d'un document.
# Utile pour simplifier les expressions XPath.
# <ead:archdesc> devient <archdesc>
doc.remove_namespaces()

# Supprimer les espaces et sauts de ligne inutiles entre les balises
# pour "minifier" le XML.
doc.remove_blank_text()

# L'indentation (pretty-printing) est gérée par la méthode .save()
doc.save("fichier_propre_et_indente.xml")
```

### Distribution d'informations (avancé)

Une fonctionnalité permet d'harmoniser les données en enrichissant un noeud parent avec une information textuelle commune à tous ses enfants. La méthode `distribute_repetition()` est conçue pour ce cas d'usage, typique de la description archivistique (ISAD-G).

Elle permet également de choisir le traitement à appliquer à l'information devenue potentiellement redondante chez les enfants.

```python
# Scénario 1: Enrichir le parent, préserver les enfants (comportement par défaut)
# Le <unittitle> du parent devient "Titre Parent : Titre Enfant Commun"
doc.distribute_repetition(
    parent_selector="//c[@level='recordgrp']",
    child_tag="c",
    target_selector="did/unittitle"
)

# Scénario 2: Enrichir le parent et supprimer le titre des enfants
doc.distribute_repetition(
    parent_selector="//c[@level='recordgrp']",
    child_tag="c",
    target_selector="did/unittitle",
    child_behavior="delete_node" # <-- On supprime le noeud <unittitle> enfant
)

# Scénario 3: Enrichir le parent et remplacer le titre des enfants par leur date
doc.distribute_repetition(
    parent_selector="//c[@level='recordgrp']",
    child_tag="c",
    target_selector="did/unittitle",
    child_behavior="replace_by_sibling", # <-- On remplace...
    sibling_selector="../unitdate"       # <-- ...par le contenu de ce noeud frère.
)
```

### API orientée objet : `EADNode`

Pour plus de confort, `nodes()` renvoie des wrappers `EADNode` avec des méthodes utilitaires.

```python
# Sélection de nœuds
for s in doc.nodes("//controlaccess/subject"):
    # Lecture du texte
    print("avant :", s.text(), s.attrs())

    # Écriture du texte et d'un attribut
    s.set_text(s.text().strip().capitalize())
    s.set_attr("encodinganalog", "610")

    # Suppression conditionnelle
    if not s.text().strip():
        s.delete()

# Texte profond (nœud + descendants) et test de sous-chaîne
for phys in doc.nodes("//physdesc"):
    if phys.text(deep=True).contains("carton"):  # insensible à la casse par défaut
        phys.delete()
```

Méthodes utiles de `EADNode` :

* `.text(deep: bool = False) -> _TextView` (chaîne avec méthode `.contains(...)`)
* `.set_text(value: str)`
* `.attrs() -> dict`
* `.get_attr(name, default=None)` / `.set_attr(name, value)` / `.del_attr(name)`
* `.children(tag: Optional[str])`
* `.xpath(expr, namespaces=None)` (retourne des `EADNode`)
* `.delete()`

### Accès bas niveau `lxml` si nécessaire

```python
# Récupérer les éléments bruts lxml
elems = doc.get_nodes("//controlaccess/subject")

# Changer le nom d'une balise (opération lxml)
for e in elems:
    e.tag = "genreform"
```

---

## Espaces de noms (namespaces)

La plupart des méthodes acceptent un paramètre `namespaces: Dict[prefix, uri]`.
Exemple :

```python
ns = {"ead3": "http://ead3.archivists.org/schema/"}
titles = doc.get("//ead3:unittitle/text()", as_text=True, namespaces=ns)
```

---

## Enregistrement

```python
# Choix de l’encodage de sortie
doc.set_output_encoding("utf-8")   # ou "preserve"
doc.save("chemin/vers/votre/fichier_transforme.xml")
```

Comportement :

* Déclaration XML réécrite avec l’encodage cible (ex. `encoding="UTF-8"` ou `ISO-8859-1"`).
* DOCTYPE d’entrée conservé, sauf si remplacé via `set_doctype(...)`.
* Indentation : `pretty_print=True` par défaut (modifie les blancs de mise en forme).

---

## Bonnes pratiques

* Travaillez sur une copie des fichiers sources.
* Lorsque les sources proviennent de systèmes hétérogènes, utilisez `encoding_override="utf-8"` au chargement et `repair_mojibake("latin1_to_utf8")`.
* Si vous manipulez EAD3 avec namespaces, fournissez systématiquement le mapping `namespaces`.
* Pour des créations de structure complexes (XPath avec prédicats, positions, namespaces), créez explicitement les éléments via `lxml` plutôt que de s’appuyer sur `_create_path`.

---

## Référence rapide de l’API

```python
# Chargement
CorrectEADDocument.load(path, parser=None, encoding_override=None)
load(path, parser=None, encoding_override=None)                 # façade

# Encodage / prologue
get_input_encoding() -> str
get_output_encoding() -> str
set_output_encoding(enc: str | "preserve")
repair_mojibake(direction="latin1_to_utf8") -> int
get_doctype() -> Optional[str]
set_doctype(doctype_decl: str) -> None
set_prelude(xml_declaration: str) -> None
save(path: Optional[str] = None, pretty_print: bool = True) -> None

# Lecture / test
get(xpath: str, as_text: bool = False, namespaces: dict | None = None) -> list
xpath(xpath: str, namespaces: dict | None = None) -> bool

# Nœuds
get_nodes(tag_or_xpath: str, namespaces: dict | None = None) -> List[etree._Element]
nodes(tag_or_xpath: str, namespaces: dict | None = None) -> List[EADNode]
first_node(tag_or_xpath: str, namespaces: dict | None = None) -> Optional[EADNode]
node_texts(tag_or_xpath, namespaces=None) -> List[str]
add(tag, text=None, attrs=None, parent_xpath="//archdesc/did", position="append", namespaces=None) -> etree._Element
delete_node(node: etree._Element) -> None

# Attributs
get_attributes(tag_or_xpath, namespaces=None) -> List[Dict[str, str]]
get_attribut(tag_or_xpath, name, namespaces=None, default=None, many=False) -> str | List[str]
set_attribut(tag_or_xpath, name, value, namespaces=None, scope="all"|"first") -> int
delete_attribut(tag_or_xpath, name, namespaces=None, scope="all"|"first") -> int
delete_attributes(tag_or_xpath, namespaces=None, keep: Iterable[str] | None = None) -> int
```

---

## Limitations et notes

* `_create_path` gère uniquement des chemins simples `//a/b/c` (sans prédicats, index, ni namespaces).
* Pas de validation DTD/XSD/RelaxNG intégrée.
* `resolve_entities=False` (les entités externes ne sont pas résolues).
* La correction *mojibake* fournie se limite au flux Latin-1→UTF-8 le plus courant.
* `pretty_print=True` peut réorganiser les blancs de mise en forme.

---

## Exemples complets

### Exemple 1 — Normalisation simple

```python
from correctead import load

doc = load("chemin/vers/votre/fichier.xml", encoding_override="utf-8")
doc.repair_mojibake("latin1_to_utf8")

if doc.get_attribut("archdesc", "level") == "fonds":
    doc.set_attribut("archdesc", "level", "recordgrp")

if not doc.xpath("//testons"):
    doc.add("testons", "Victor Hugo",
            attrs={"authfilenumber": "BnF10293"},
            parent_xpath="//archdesc/did")

doc.set_doctype(
    '<!DOCTYPE ead PUBLIC '
    '"//ISBN 1-931666-00-8//DTD ead.dtd (Encoded Archival Description (EAD) Version 2002)//EN" '
    '"/gaia/normes/ead.dtd">'
)

doc.set("//publicationstmt/date", "Juillet 2026")

for s in doc.nodes("//controlaccess/subject"):
    s.set_text(s.text().strip().capitalize())
    s.set_attr("encodinganalog", "610")

# Remplacer tous les <subject> par <genreform> (opération lxml)
for e in doc.get_nodes("//controlaccess/subject"):
    e.tag = "genreform"

doc.set_output_encoding("utf-8")
doc.save("chemin/vers/votre/fichier_transforme.xml")
```

### Exemple 2 — Préservation de l’encodage d’entrée

```python
from correctead import load

doc = load("chemin/vers/votre/fichier_iso.xml")      # suppose ISO-8859-1 correctement déclaré
print("in:", doc.get_input_encoding())
doc.set_output_encoding("preserve")  # conserver ISO-8859-1 à la sortie
doc.save("chemin/vers/votre/fichier_preserve.xml")
```

---
```
pip install git+https://github.com/desireesdata/correctEAD.git@package
PYTHONPATH=src python3 exemple.py
ou python sans 3 !
```

Créer un environnement virtuel avant.

