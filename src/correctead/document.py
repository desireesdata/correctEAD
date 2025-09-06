from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable, Union, Any, Dict
from lxml import etree
import io
import re

from .node import EADNode
from .encoding import _canon_enc, repair_mojibake
from .exceptions import CorrectEADError

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
        self._input_encoding = enc_in
        self._output_encoding = "preserve"

    def get_input_encoding(self) -> str:
        return self._input_encoding

    def get_output_encoding(self) -> str:
        return self._output_encoding

    def set_output_encoding(self, enc: str) -> None:
        if not enc:
            raise ValueError("Encodage de sortie vide ou invalide.")
        self._output_encoding = "preserve" if enc.strip().lower() == "preserve" else _canon_enc(enc)

    @classmethod
    def load(cls, path: str, parser: Optional[etree.XMLParser] = None, encoding_override: Optional[str] = None) -> "CorrectEADDocument":
        if parser is None:
            parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)

        if encoding_override:
            with open(path, "rb") as f:
                raw = f.read()
            text = raw.decode(encoding_override)
            bio = io.BytesIO(text.encode("utf-8"))
            tree = etree.parse(bio, parser)
            doc = cls(tree, source_path=path)
            doc._input_encoding = encoding_override.lower()
            return doc
        else:
            tree = etree.parse(path, parser)
            return cls(tree, source_path=path)

    def repair_mojibake(self, direction: str = "latin1_to_utf8") -> int:
        return repair_mojibake(self._tree, direction=direction)

    def save(self, path: Optional[str] = None, pretty_print: bool = True) -> None:
        out_path = path or self._source_path
        if out_path is None:
            raise ValueError("Aucun chemin cible fourni pour l'enregistrement.")

        target_enc = self._input_encoding if self._output_encoding == "preserve" else self._output_encoding
        target_enc = _canon_enc(target_enc)

        xml_text = etree.tostring(
            self._tree.getroot(),
            xml_declaration=False,
            encoding="unicode",
            pretty_print=pretty_print,
            with_tail=False,
        )

        xml_decl = self._build_xml_declaration_for_encoding(target_enc)
        parts = [xml_decl]
        if self._prelude.doctype:
            parts.append(self._prelude.doctype)
        parts.append(xml_text)
        final_text = "\n".join(parts)
        if not final_text.endswith("\n"):
            final_text += "\n"

        final_bytes = final_text.encode(target_enc, errors="xmlcharrefreplace")
        with open(out_path, "wb") as f:
            f.write(final_bytes)

    def get_doctype(self) -> Optional[str]:
        return self._prelude.doctype

    def set_doctype(self, doctype_decl: str) -> None:
        cleaned = doctype_decl.strip()
        if not (cleaned.startswith("<!DOCTYPE") and cleaned.endswith(">")):
            raise ValueError("Le DOCTYPE doit être fourni tel quel, incluant <!DOCTYPE ...> et le > final.")
        self._prelude.doctype = cleaned

    def set_prelude(self, xml_declaration: str) -> None:
        cleaned = xml_declaration.strip()
        if not (cleaned.startswith("<?xml") and cleaned.endswith("?>")):
            raise ValueError("La déclaration XML doit être du type '<?xml ... ?>'.")
        self._prelude.xml_decl = cleaned

    def get(self, xpath: str, as_text: bool = False, namespaces: Optional[Dict[str, str]] = None) -> Union[List[etree._Element], List[Any]]:
        res = self._tree.xpath(xpath, namespaces=namespaces)
        if as_text:
            return [self._atom_to_text(x) for x in res]
        return res

    def xpath(self, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> bool:
        res = self._tree.xpath(xpath, namespaces=namespaces)
        return bool(res)

    def add(
        self,
        tag: str,
        text: Optional[str] = None,
        attrs: Optional[Dict[str, str]] = None,
        parent_xpath: str = "//archdesc/did",
        position: str = "append",
        namespaces: Optional[Dict[str, str]] = None,
    ) -> etree._Element:
        parents = self._tree.xpath(parent_xpath, namespaces=namespaces)
        if not parents:
            raise CorrectEADError(f"Parent introuvable pour parent_xpath={parent_xpath}")
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

    def wrap(self, elem) -> EADNode:
        return EADNode(elem)

    def nodes(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[EADNode]:
        elems = self.get_nodes(tag_or_xpath, namespaces=namespaces)
        return [EADNode(e) for e in elems]

    def first_node(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None) -> Optional[EADNode]:
        ns = self.nodes(tag_or_xpath, namespaces=namespaces)
        return ns[0] if ns else None

    def node_texts(self, tag_or_xpath, namespaces=None):
        return [(n.text() or "").strip() for n in self.nodes(tag_or_xpath, namespaces=namespaces)]

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
        nodes = self._tree.xpath(xpath, namespaces=namespaces)

        if nodes:
            for node in nodes:
                if isinstance(node, etree._Element):
                    node.text = value
        elif create:
            self._create_path(xpath, value, namespaces)

    def _create_path(
        self, xpath: str, value: str, namespaces: Optional[Dict[str, str]] = None
    ) -> etree._Element:
        if not xpath.startswith("//"):
            raise CorrectEADError(
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
    
    def _resolve_nodes(self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None):
        if tag_or_xpath.startswith("/") or tag_or_xpath.startswith(".") or tag_or_xpath.startswith("//"):
            q = tag_or_xpath
        else:
            q = f"//{tag_or_xpath}"
        return [n for n in self._tree.xpath(q, namespaces=namespaces) if isinstance(n, etree._Element)]

    def _build_xml_declaration_for_encoding(self, target_enc: str) -> str:
        decl = (self._prelude.xml_decl or "").strip()
        version = self._tree.docinfo.xml_version or "1.0"

        if not decl:
            return f'<?xml version="{version}" encoding="{target_enc}"?>'

        if 'encoding="' in decl:
            decl = re.sub(r'encoding="[^"]*"', f'encoding="{target_enc}"', decl)
        else:
            decl = decl.rstrip()
            if decl.endswith("?>"):
                decl = decl[:-2].rstrip()
                if decl.startswith("<?xml"):
                    decl = f'{decl} encoding="{target_enc}"?>'
                else:
                    decl = f'<?xml version="{version}" encoding="{target_enc}"?>'
            else:
                decl = f'<?xml version="{version}" encoding="{target_enc}"?>'
        return decl

    def get_attributes(
        self, tag_or_xpath: str, namespaces: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, str]]:
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
        scope: str = "all",
    ) -> int:
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
        scope: str = "all",
    ) -> int:
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
        nodes = self._resolve_nodes(tag_or_xpath, namespaces)
        kset = set(keep or [])
        affected = 0
        for n in nodes:
            if not n.attrib:
                continue
            if kset:
                for a in list(n.attrib.keys()):
                    if a not in kset:
                        del n.attrib[a]
            else:
                n.attrib.clear()
            affected += 1
        return affected
