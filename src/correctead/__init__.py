"""correctEAD: A simple tool for EAD XML correction."""

__version__ = "0.1.0"

from .document import CorrectEADDocument
from .node import EADNode
from .exceptions import CorrectEADError

def load(path: str, parser = None, encoding_override: str | None = None) -> CorrectEADDocument:
    """Facade for loading an EAD document."""
    return CorrectEADDocument.load(path, parser=parser, encoding_override=encoding_override)

__all__ = ["CorrectEADDocument", "EADNode", "CorrectEADError", "load"]
