"""OCR contrôlée des scans de sujets d'examen (étape 2 du pipeline Data-Low).

Le manuscrit impose une *OCR contrôlée* : chaque page est traitée par deux
moteurs (Tesseract via PyTesseract et, lorsqu'il est installé, le moteur
PDF natif PyMuPDF), les deux sorties sont alignées et les écarts au-delà
d'un seuil de similarité sont marqués pour relecture humaine. Un exercice
dont le texte OCR est douteux ne doit jamais entrer dans le corpus sans
revue : c'est ce que garantit la classe :class:`PageOCR`.

Le seuil de similarité par défaut (0.90) reflète la tolérance retenue lors
de la phase pilote : les formules mathématiques produisent presque
toujours des divergences entre moteurs, mais un écart global supérieur à
10 % signale une page mal scannée ou un composé mathématique complexe.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("loweval.data_low.ocr")

#: Similarité minimale entre les deux moteurs pour accepter une page sans
#: relecture ; sous ce seuil, ``a_relire`` vaut True (contrôle humain).
SEUIL_SIMILARITE = 0.90


@dataclass
class PageOCR:
    """Résultat de l'OCR d'une page de sujet.

    Attributes:
        chemin: fichier source (scan ou PDF).
        page: numéro de page (1-based ; 0 pour un scan image unique).
        texte: transcription retenue (celle du moteur le plus long, censée
            être la plus complète).
        similarite: similarité entre les deux moteurs dans [0, 1].
        a_relire: True si la similarité est sous le seuil → relecture
            humaine obligatoire avant insertion dans le corpus.
        moteurs: texte brut de chaque moteur (pour l'audit).
    """

    chemin: Path
    page: int
    texte: str
    similarite: float
    a_relire: bool
    moteurs: dict[str, str] = field(default_factory=dict)


def _ocr_tesseract(chemin: Path) -> str:
    """Lance Tesseract sur une image (PNG/JPEG/TIFF) ou extrait le texte
    d'un PDF page par page via un rendu intermédiaire.

    Import paresseux : pytesseract/PIL ne sont requis que si cette fonction
    est réellement appelée, ce qui permet d'utiliser le reste du kit sur des
    machines sans dépendances OCR.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dépendance optionnelle
        raise RuntimeError(
            "OCR Tesseract indisponible : installez pytesseract + tesseract-ocr."
        ) from exc

    if chemin.suffix.lower() == ".pdf":
        # Rendu PDF → image via PyMuPDF, puis OCR classique page à page.
        import fitz

        textes: list[str] = []
        with fitz.open(chemin) as document:
            for page_pdf in document:
                pix = page_pdf.get_pixmap(dpi=200)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                textes.append(pytesseract.image_to_string(image, lang="fra"))
        return "\n".join(textes)

    return pytesseract.image_to_string(Image.open(chemin), lang="fra")


def _ocr_pymupdf(chemin: Path) -> str:
    """Extraction native du texte d'un PDF (couche texte, sans OCR).

    Retourne une chaîne vide pour les images sans couche texte : c'est le
    signal qui fait basculer la décision finale sur Tesseract seul.
    """
    try:
        import fitz
    except ImportError:  # pragma: no cover - dépendance optionnelle
        return ""
    if chemin.suffix.lower() != ".pdf":
        return ""
    with fitz.open(chemin) as document:
        return "\n".join(page.get_text() for page in document)


def similarite_texte(a: str, b: str) -> float:
    """Similarité normalisée entre deux transcriptions (ratio de difflib)."""
    if not a.strip() and not b.strip():
        return 1.0  # deux pages vides s'accordent parfaitement
    return difflib.SequenceMatcher(None, a, b).ratio()


def ocr_controle(chemin: Path | str, page: int = 0) -> PageOCR:
    """Exécute l'OCR contrôlée d'un fichier et décide si une relecture est requise.

    Stratégie de décision :
      1. lancer les deux moteurs (Tesseract, PyMuPDF) ;
      2. si l'un est vide, la similarité ne peut pas être calculée : on
         retient le texte non vide mais on impose une relecture (sauf si
         les deux sont vides) ;
      3. sinon, similarité = ratio de difflib ; sous le seuil → relecture.
    """
    chemin = Path(chemin)
    logger.info("OCR contrôlée de %s", chemin.name)

    tesseract = _ocr_tesseract(chemin).strip()
    natif = _ocr_pymupdf(chemin).strip()

    # Cas dégénérés : un seul moteur a produit du texte.
    if not tesseract or not natif:
        texte = tesseract or natif
        return PageOCR(
            chemin=chemin,
            page=page,
            texte=texte,
            similarite=1.0 if texte == "" else 0.0,
            a_relire=bool(texte),  # texte sans second avis → relecture
            moteurs={"tesseract": tesseract, "pymupdf": natif},
        )

    sim = similarite_texte(tesseract, natif)
    a_relire = sim < SEUIL_SIMILARITE
    # Retenir la transcription la plus longue : elle est généralement la
    # plus complète (le moteur le plus bref a souvent raté des zones).
    texte = tesseract if len(tesseract) >= len(natif) else natif
    if a_relire:
        logger.warning(
            "Page %s : similarité %.2f sous le seuil %.2f → relecture humaine",
            chemin.name, sim, SEUIL_SIMILARITE,
        )
    return PageOCR(
        chemin=chemin,
        page=page,
        texte=texte,
        similarite=round(sim, 3),
        a_relire=a_relire,
        moteurs={"tesseract": tesseract, "pymupdf": natif},
    )
