from __future__ import annotations
from typing import List, Optional

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
