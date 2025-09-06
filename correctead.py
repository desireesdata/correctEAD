from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable, Union, Any, Dict
from lxml import etree
import io
import re

def _canon_enc(name: str) -> str:
    if not name:
        return "UTF-8"
    n = name.strip().lower()
    if n in {"utf8", "utf-8"}:
        return "UTF-8"
    if n in {"latin1", "latin-1", "iso8859-1", "iso-8859-1"}:
        return "ISO-8859-1"
    return name 

class _TextView(str):
    def contains(
        self,
        needle: str,
        *,
        case_insensitive: bool = True,
        normalize_spaces: bool = True,
        whole_word: bool = False,
    ) -> bool:
        """
        Vérifie si 'needle' est présent dans la chaîne.
        - case_insensitive : comparaison insensible à la casse
        - normalize_spaces : compresse les espaces (multi→simple) avant test
        - whole_word       : teste par mots (délimités par espaces) au lieu de sous-chaîne
        """
        s = self
        if normalize_spaces:
            s = " ".join(s.split())
        n = str(needle)
        if case_insensitive:
            s, n = s.casefold(), n.casefold()
        if whole_word:
            return n in set(s.split())
        return n in s

class EADNode:
    """
    Enveloppe légère autour d'un lxml Element pour offrir une API plus “objet”.
    Ne modifie pas l'élément sous-jacent (accès via .element).
    """
    def __init__(self, element):
        self.element = element  # lxml.etree._Element

    # --- Infos basiques ---
    @property
    def tag(self) -> str:
        return self.element.tag

    def text(self) -> str:
        return self.element.text or ""

    def set_text(self, value: str) -> None:
        self.element.text = value

    # --- Attributs ---
    def attrs(self) -> dict:
        return dict(self.element.attrib)

    def get_attr(self, name: str, default=None):
        return self.element.get(name, default)

    def set_attr(self, name: str, value: str) -> None:
        self.element.set(name, value)

    def del_attr(self, name: str) -> bool:
        if name in self.element.attrib:
            del self.element.attrib[name]
            return True
        return False

    # --- Navigation ---
    def children(self, tag: str | None = None) -> list["EADNode"]:
        if tag:
            return [EADNode(e) for e in self.element.findall(tag)]
        return [EADNode(e) for e in list(self.element)]

    def xpath(self, expr: str, namespaces: dict | None = None) -> list["EADNode"]:
        res = self.element.xpath(expr, namespaces=namespaces)
        return [EADNode(e) for e in res if hasattr(e, "tag")]  # on ne wrappe que les éléments

    # --- Mutation structurelle ---
    def delete(self) -> None:
        parent = self.element.getparent()
        if parent is not None:
            parent.remove(self.element)

    # --- Représentation utile au debug ---
    def __repr__(self) -> str:
        tid = self.element.get("id")
        lbl = f" id={tid!r}" if tid else ""
        return f"<EADNode <{self.tag}{lbl}> text={self.text()!r}>"
    
    def text(self, deep: bool = False) -> _TextView:
        """
        Texte du nœud.
        - deep=False (défaut) : texte immédiat
        - deep=True           : texte du nœud + descendants (équiv. string(.))
        """
        if deep:
            s = "".join(self.element.itertext())
        else:
            s = self.element.text or ""
        return _TextView(s)


@dataclass
class _Prelude:
    xml_decl: str = '<?xml version="1.0" encoding="utf-8"?>'
    doctype: Optional[str] = None  # ex: '<!DOCTYPE ead PUBLIC "...">'

class CorrectEADDocument:
    def __init__(self, tree: etree._ElementTree, source_path: Optional[str] = None):
        self._tree = tree
        self._source_path = source_path
        self._prelude = _Prelude()

        # 1) Conserver le DOCTYPE d'origine s'il existe
        if getattr(tree.docinfo, "doctype", None):
            self._prelude.doctype = tree.docinfo.doctype

        # 2) Déterminer version XML et encodage d'entrée (canonisé)
        xml_version = getattr(tree.docinfo, "xml_version", None) or "1.0"
        enc_in_raw = getattr(tree.docinfo, "encoding", None) or "UTF-8"
        enc_in = _canon_enc(enc_in_raw)

        # 3) Déclaration XML initiale (sera ré-alignée à l'export si besoin)
        self._prelude.xml_decl = f'<?xml version="{xml_version}" encoding="{enc_in}"?>'

        # 4) Politique d'encodage
        #    - _input_encoding : encodage réellement utilisé à l'entrée
        #    - _output_encoding : "preserve" (par défaut) → réécrit dans l'encodage d'entrée
        self._input_encoding = enc_in
        self._output_encoding = "preserve"

        # ---------- Encodage : API publique ----------
    def get_input_encoding(self) -> str:
        """Encodage détecté/déclaré lors du chargement."""
        return self._input_encoding

    def get_output_encoding(self) -> str:
        """
        Encodage choisi pour la sortie.
        - 'preserve'  : réutiliser l'encodage d'entrée
        - autrement   : nom d'encodage explicite (ex. 'utf-8', 'iso-8859-1')
        """
        return self._output_encoding

    def set_output_encoding(self, enc: str) -> None:
        if not enc:
            raise ValueError("Encodage de sortie vide ou invalide.")
        self._output_encoding = "preserve" if enc.strip().lower() == "preserve" else _canon_enc(enc)


    # ---------- Chargement / sauvegarde ----------
    @classmethod
    def load(cls, path: str, parser: Optional[etree.XMLParser] = None, encoding_override: Optional[str] = None) -> "CorrectEADDocument":
        """
        Charge un XML.
        - encoding_override: si fourni, on IGNORE la déclaration du fichier et on force
          le décodage initial avec cet encodage (utile si la déclaration est fausse).
        """
        if parser is None:
            parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)

        if encoding_override:
            # Lire les octets, décoder avec l'override, puis reparser via BytesIO en UTF-8
            with open(path, "rb") as f:
                raw = f.read()
            # On décode selon l'override (si échec -> UnicodeDecodeError)
            text = raw.decode(encoding_override)
            # On reparse depuis des octets UTF-8 - la déclaration interne d'encodage
            # est ignorée à ce stade par libxml2, mais on conservera le DOCTYPE.
            bio = io.BytesIO(text.encode("utf-8"))
            tree = etree.parse(bio, parser)
            doc = cls(tree, source_path=path)
            # Encodage d'entrée logique = override (pas celui vu par docinfo)
            doc._input_encoding = encoding_override.lower()
            return doc
        else:
            tree = etree.parse(path, parser)
            return cls(tree, source_path=path)
        
        # ---------- Réparation manuelle de mojibake ----------
    def repair_mojibake(self, direction: str = "latin1_to_utf8") -> int:
        """
        Répare certains cas où le texte a été mal décodé auparavant.
        - direction='latin1_to_utf8' : corrige "SociÃ©tÃ©" -> "Société"
        Renvoie le nombre de champs modifiés.
        """
        if direction != "latin1_to_utf8":
            raise ValueError("Seule la direction 'latin1_to_utf8' est prise en charge pour l'instant.")

        def maybe_fix(s: Optional[str]) -> Optional[str]:
            if not s:
                return s
            # Heuristique : ne tente que si l'on voit des séquences typiques de mojibake
            if ("Ã" in s) or ("Â" in s) or ("â" in s and "€™" in s):
                try:
                    fixed = s.encode("latin-1").decode("utf-8")
                    # Si la correction produit plus de lettres accentuées utiles, on la garde
                    return fixed
                except Exception:
                    return s
            return s

        changed = 0
        for el in self._tree.getroot().iter():
            t = el.text
            new_t = maybe_fix(t)
            if new_t != t:
                el.text = new_t
                changed += 1
            tail = el.tail
            new_tail = maybe_fix(tail)
            if new_tail != tail:
                el.tail = new_tail
                changed += 1
        return changed

    def save(self, path: Optional[str] = None, pretty_print: bool = True) -> None:
        out_path = path or self._source_path
        if out_path is None:
            raise ValueError("Aucun chemin cible fourni pour l'enregistrement.")

        target_enc = self._input_encoding if self._output_encoding == "preserve" else self._output_encoding
        target_enc = _canon_enc(target_enc)  # ou self._canon_enc(...)

        # 1) sérialiser la racine en UNICODE
        xml_text = etree.tostring(
            self._tree.getroot(),
            xml_declaration=False,
            encoding="unicode",
            pretty_print=pretty_print,
            with_tail=False,
        )

        # 2) prologue en UNICODE
        xml_decl = self._build_xml_declaration_for_encoding(target_enc)
        parts = [xml_decl]
        if self._prelude.doctype:
            parts.append(self._prelude.doctype)
        parts.append(xml_text)
        final_text = "\n".join(parts)
        if not final_text.endswith("\n"):
            final_text += "\n"

        # 3) un SEUL encodage final puis écriture binaire
        final_bytes = final_text.encode(target_enc, errors="xmlcharrefreplace")
        with open(out_path, "wb") as f:
            f.write(final_bytes)


    # ---------- Accès DOCTYPE / prologue ----------
    def get_doctype(self) -> Optional[str]:
        return self._prelude.doctype

    def set_doctype(self, doctype_decl: str) -> None:
        """
        doctype_decl doit être une chaîne complète du type:
        '<!DOCTYPE ead PUBLIC "ISBN 1-931666-00-8 (EAD 2002)" "/gaia/normes/ead.dtd">'
        """
        cleaned = doctype_decl.strip()
        if not (cleaned.startswith("<!DOCTYPE") and cleaned.endswith(">")):
            raise ValueError("Le DOCTYPE doit être fourni tel quel, incluant <!DOCTYPE ...> et le > final.")
        self._prelude.doctype = cleaned

    def set_prelude(self, xml_declaration: str) -> None:
        """
        xml_declaration ex: '<?xml version="1.0" encoding="utf-8"?>'
        """
        cleaned = xml_declaration.strip()
        if not (cleaned.startswith("<?xml") and cleaned.endswith("?>")):
            raise ValueError("La déclaration XML doit être du type '<?xml ... ?>'.")
        self._prelude.xml_decl = cleaned

    # ---------- XPath utilitaires ----------
    def get(self, xpath: str, as_text: bool = False, namespaces: Optional[Dict[str, str]] = None) -> Union[List[etree._Element], List[Any]]:
        """
        Renvoie le résultat XPath. Si as_text=True, convertit les items atomiques en str.
        """
        res = self._tree.xpath(xpath, namespaces=namespaces)
        if as_text:
            return [self._atom_to_text(x) for x in res]
        return res

    def xpath(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> bool:
        """
        Renvoie True si le XPath retourne au moins 1 résultat, sinon False.
        """
        res = self._tree.xpath(xpath, namespaces=namespaces)
        return bool(res)

    # ---------- Ajout / suppression / navigation ----------
    def add(
        self,
        tag: str,
        text: Optional[str] = None,
        attrs: Optional[Dict[str, str]] = None,
        parent_xpath: str = "//archdesc/did",
        position: str = "append",
        namespaces: Optional[Dict[str, str]] = None,
    ) -> etree._Element:
        """
        Ajoute un élément <tag> sous le parent (par défaut //archdesc/did).
        position: 'append' (fin), 'prepend' (début)
        """
        parents = self._tree.xpath(parent_xpath, namespaces=namespaces)
        if not parents:
            raise ValueError(f"Parent introuvable pour parent_xpath={parent_xpath}")
        parent = parents[0]

        elem = etree.Element(tag)
        if attrs:
            for k, v in attrs.items():
                elem.set(k, v)
        if text is not None:
            elem.text = text

        if position == "append":
            parent.append(elem)
        elif position == "prepend":
            parent.insert(0, elem)
        else:
            raise ValueError("position doit être 'append' ou 'prepend'.")

        return elem

    def get_nodes(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[etree._Element]:
        """
        Si l'argument ne commence pas par '/', '.', ou '//' on le traite comme un nom de tag simple.
        """
        if tag_or_xpath.startswith("/") or tag_or_xpath.startswith(".") or tag_or_xpath.startswith("//"):
            q = tag_or_xpath
        else:
            q = f"//{tag_or_xpath}"
        res = self._tree.xpath(q, namespaces=namespaces)
        return [n for n in res if isinstance(n, etree._Element)]

    def delete_node(self, node: etree._Element) -> None:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    # À ajouter dans la classe CorrectEADDocument (près de get_nodes)
    # ---------- Version “wrappee” : EADNode ----------
    def wrap(self, elem) -> EADNode:
        return EADNode(elem)

    def nodes(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[EADNode]:
        """
        Comme get_nodes(), mais renvoie des EADNode.
        """
        elems = self.get_nodes(tag_or_xpath, namespaces=namespaces)
        return [EADNode(e) for e in elems]

    def first_node(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None) -> Optional[EADNode]:
        ns = self.nodes(tag_or_xpath, namespaces=namespaces)
        return ns[0] if ns else None

    def node_texts(self, tag_or_xpath, namespaces=None):
        return [(n.text() or "").strip() for n in self.nodes(tag_or_xpath, namespaces=namespaces)]

    # ---------- Helpers ----------
    @property
    def root(self) -> etree._Element:
        return self._tree.getroot()

    @staticmethod
    def _atom_to_text(x: Any) -> str:
        if isinstance(x, (str, bytes)):
            return x.decode("utf-8") if isinstance(x, bytes) else x
        return str(x)
    
    def set(
        self,
        xpath: str,
        value: str,
        namespaces: Optional[Dict[str, str]] = None,
        create: bool = True,
    ) -> None:
        """
        Modifie (ou crée) le/les nœuds trouvés par XPath et leur assigne `value`.

        - `xpath`: ex. "//publicationstmt/date"
        - `value`: texte à insérer
        - `create`: si True, crée la chaîne de tags si le chemin n'existe pas
        """
        nodes = self._tree.xpath(xpath, namespaces=namespaces)

        if nodes:
            for node in nodes:
                if isinstance(node, etree._Element):
                    node.text = value
        elif create:
            # Création de la structure manquante
            self._create_path(xpath, value, namespaces)

    # --- Helper interne pour créer la structure manquante ---
    def _create_path(
        self, xpath: str, value: str, namespaces: Optional[Dict[str, str]] = None
    ) -> etree._Element:
        """
        Crée récursivement les éléments manquants pour atteindre le XPath simple
        (chemins de type //a/b/c uniquement, pas de predicates complexes).
        """
        if not xpath.startswith("//"):
            raise ValueError(
                "La création automatique ne gère que les chemins de type //a/b/c."
            )

        parts = xpath.strip("/").split("/")
        current = self.root
        for part in parts:
            found = current.find(part)
            if found is None:
                found = etree.Element(part)
                current.append(found)
            current = found
        current.text = value
        return current
    
        # --- Helpers de sélection (déjà proche de get_nodes) ---
    def _resolve_nodes(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None):
        if tag_or_xpath.startswith("/") or tag_or_xpath.startswith(".") or tag_or_xpath.startswith("//"):
            q = tag_or_xpath
        else:
            q = f"//{tag_or_xpath}"
        return [n for n in self._tree.xpath(q, namespaces=namespaces) if isinstance(n, etree._Element)]

        # ---------- Helpers déclaration XML ----------
    def _build_xml_declaration_for_encoding(self, target_enc: str) -> str:
        """
        Si l'utilisateur a fourni une déclaration via set_prelude(), on ajuste
        (ou insère) l'attribut encoding=... pour correspondre à target_enc.
        Sinon, on génère une déclaration standard.
        """
        decl = (self._prelude.xml_decl or "").strip()
        version = self._tree.docinfo.xml_version or "1.0"

        if not decl:
            return f'<?xml version="{version}" encoding="{target_enc}"?>'

        # Normaliser/forcer l'attribut encoding="..."
        # - s'il existe, on le remplace
        # - sinon, on l'insère avant la fermeture ?>
        if 'encoding="' in decl:
            decl = re.sub(r'encoding="[^"]*"', f'encoding="{target_enc}"', decl)
        else:
            # insérer encoding avant '?>'
            decl = decl.rstrip()
            if decl.endswith("?>"):
                decl = decl[:-2].rstrip()
                # s'il n'y a pas déjà une version, on garde telle quelle
                if decl.startswith("<?xml"):
                    decl = f'{decl} encoding="{target_enc}"?>'
                else:
                    decl = f'<?xml version="{version}" encoding="{target_enc}"?>'
            else:
                # en cas de forme exotique, on repart sainement
                decl = f'<?xml version="{version}" encoding="{target_enc}"?>'
        return decl

    # ================= ATTRIBUTS =================

    def get_attributes(
        self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, str]]:
        """
        Retourne, pour chaque nœud correspondant, un dict {attr: valeur}.
        """
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        return [dict(n.attrib) for n in nodes]

    def get_attribut(
        self,
        tag_or_xpath: str,
        name: str,
        namespaces: Optional[Dict[str, str]] = None,
        default: Optional[str] = None,
        many: bool = False,
    ) -> Union[Optional[str], List[Optional[str]]]:
        """
        Récupère la/les valeur(s) d'un attribut.
        - many=False (défaut) : renvoie la 1re valeur trouvée (ou default si rien).
        - many=True : renvoie une liste alignée sur les nœuds.
        """
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        if many:
            return [n.get(name, default) for n in nodes]
        return nodes[0].get(name, default) if nodes else default

    def set_attribut(
        self,
        tag_or_xpath: str,
        name: str,
        value: str,
        namespaces: Optional[Dict[str, str]] = None,
        scope: str = "all",  # 'all' | 'first'
    ) -> int:
        """
        Définit (crée/remplace) l'attribut sur les nœuds correspondants.
        Renvoie le nombre de nœuds modifiés.
        """
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        if not nodes:
            return 0
        if scope == "first":
            nodes = nodes[:1]
        for n in nodes:
            n.set(name, value)
        return len(nodes)

    def delete_attribut(
        self,
        tag_or_xpath: str,
        name: str,
        namespaces: Optional[Dict[str, str]] = None,
        scope: str = "all",  # 'all' | 'first'
    ) -> int:
        """
        Supprime l'attribut 'name' s'il est présent. Renvoie le nb de suppressions.
        """
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        if scope == "first":
            nodes = nodes[:1]
        count = 0
        for n in nodes:
            if name in n.attrib:
                del n.attrib[name]
                count += 1
        return count

    def delete_attributes(
        self,
        tag_or_xpath: str,
        namespaces: Optional[Dict[str, str]] = None,
        keep: Optional[Iterable[str]] = None,
    ) -> int:
        """
        Supprime tous les attributs des nœuds correspondants.
        Optionnellement conserver une liste 'keep' (ex. ['id']).
        Renvoie le nb de nœuds affectés.
        """
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        kset = set(keep or [])
        affected = 0
        for n in nodes:
            if not n.attrib:
                continue
            if kset:
                # ne retirer que ceux qui ne sont pas dans 'keep'
                for a in list(n.attrib.keys()):
                    if a not in kset:
                        del n.attrib[a]
            else:
                n.attrib.clear()
            affected += 1
        return affected


# API de façade "correctead.load"
def load(path: str,
         parser: Optional[etree.XMLParser] = None,
         encoding_override: Optional[str] = None) -> CorrectEADDocument:
    return CorrectEADDocument.load(path, parser=parser, encoding_override=encoding_override)
