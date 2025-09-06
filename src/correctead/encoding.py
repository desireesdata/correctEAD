from typing import Optional
from lxml import etree

def _canon_enc(name: str) -> str:
    if not name:
        return "UTF-8"
    n = name.strip().lower()
    if n in {"utf8", "utf-8"}:
        return "UTF-8"
    if n in {"latin1", "latin-1", "iso8859-1", "iso-8859-1"}:
        return "ISO-8859-1"
    return name

def repair_mojibake(tree: etree._ElementTree, direction: str = "latin1_to_utf8") -> int:
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
    for el in tree.getroot().iter():
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
