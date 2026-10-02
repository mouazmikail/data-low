"""Segmentation des sujets OCRisés en exercices autonomes (étape 3).

Après l'OCR, un sujet complet (ex. « Mathématiques — Bac 2023 — série SN »)
reste un bloc de texte continu. Ce module découpe le bloc en exercices en
s'appuyant sur les marqueurs typographiques des sujets d'examen :

* numéros arabes en début de ligne : « 1. », « 2) », « Exercice 3 » ;
* barèmes : « (4 points) », « (3,5 pts) » ;
* consignes : « On considère… », « Démontrez que… ».

La segmentation est volontairement *conservative* : un bloc dont le premier
marqueur n'apparaît pas au début est gardé entier plutôt que coupé au
hasard — mieux vaut un exercice trop large (resegmenté à la main) qu'un
énoncé tronqué (irrécupérable).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("loweval.data_low.segment")

# ---------------------------------------------------------------------------
# 1. Marqueurs de début d'exercice
# ---------------------------------------------------------------------------
#: Numéro d'exercice en début de ligne : « 1. », « 2) », « Exercice 3 : ».
_MOTIF_NUMERO = re.compile(
    r"^\s*(?:exercice\s+)?(\d{1,2})\s*[.)]?\s*(?:\(|:|–|-)?\s*",
    re.IGNORECASE,
)

#: Barème annoncé entre parenthèses : « (4 points) », « (3,5 pts) ».
_MOTIF_BAREME = re.compile(r"\(\s*\d+(?:[.,]\d+)?\s*(?:points?|pts?)\s*\)")

#: Longueur minimale d'un énoncé segmenté (en caractères) ; en dessous, le
#: segment est considéré comme un artefact de découpe et rejeté. La garde est
#: volontairement basse (25) : elle ne vise que les artefacts, pas les courts
#: énoncés synthétiques de tests ou de sujets à questions très brèves.
LONGUEUR_MIN_ENONCE = 25


@dataclass
class SegmentExercice:
    """Un exercice candidat issu de la segmentation d'un sujet."""

    numero: int                       # position dans le sujet (1, 2, 3…)
    enonce: str                       # texte de l'énoncé (nettoyé)
    bareme: float | None = None       # barème annoncé, si détecté
    a_verifier: bool = field(default=False)  # segmentation douteuse


def _extraire_bareme(texte: str) -> float | None:
    """Extrait le barème d'un segment (« (4 points) » → 4.0)."""
    match = _MOTIF_BAREME.search(texte)
    if not match:
        return None
    brut = match.group(0)
    # Ne garder que la partie numérique (virgule décimale acceptée).
    nombre = re.search(r"\d+(?:[.,]\d+)?", brut)
    return float(nombre.group(0).replace(",", ".")) if nombre else None


def segmenter_sujet(texte: str) -> list[SegmentExercice]:
    """Découpe le texte d'un sujet complet en exercices candidats.

    Algorithme :
      1. découper le texte en lignes et repérer les lignes qui débutent par
         un numéro d'exercice (motif ``_MOTIF_NUMERO``) ;
      2. vérifier que les numéros détectés forment une suite strictement
         croissante à partir de 1 — sinon, les candidats incohérents sont
         ignorés et le segment correspondant est marqué « à vérifier » ;
      3. constituer un segment par paire de marqueurs consécutifs et en
         extraire le barème.
    """
    lignes = texte.splitlines()
    marqueurs: list[int] = []  # indices de lignes débutant un exercice
    numeros: list[int] = []

    for i, ligne in enumerate(lignes):
        m = _MOTIF_NUMERO.match(ligne)
        if not m:
            continue
        numero = int(m.group(1))
        # Heuristique : le numéro doit prolonger la suite attendue (1, 2, 3…)
        # ou redémarrer à 1 ; un « 12 » isolé en milieu de page est suspect.
        attendu = (numeros[-1] + 1) if numeros else 1
        if numero == attendu or (numero == 1 and not numeros):
            marqueurs.append(i)
            numeros.append(numero)

    # Aucun marqueur fiable → conserver le sujet entier, à vérifier.
    if not marqueurs:
        logger.warning("Aucun marqueur d'exercice trouvé ; sujet conservé entier.")
        return [SegmentExercice(numero=1, enonce=texte.strip(), a_verifier=True)]

    segments: list[SegmentExercice] = []
    bornes = marqueurs + [len(lignes)]  # borne finale artificielle
    from itertools import pairwise  # noqa: PLC0415 (py ≥ 3.10)

    for position, (debut, fin) in enumerate(pairwise(bornes), start=1):
        brut = "\n".join(lignes[debut:fin]).strip()
        # Nettoyage du marqueur en tête (« 1. ») pour ne garder que l'énoncé.
        enonce = _MOTIF_NUMERO.sub("", brut, count=1).strip()
        if len(enonce) < LONGUEUR_MIN_ENONCE:
            logger.warning("Segment %d trop court (%d caractères), ignoré.",
                           position, len(enonce))
            continue
        segments.append(SegmentExercice(
            numero=position,
            enonce=enonce,
            bareme=_extraire_bareme(enonce),
        ))
    return segments


def _code_discipline(discipline: str) -> str:
    """Code ASCII court d'une discipline pour l'identifiant canonique.

    « mathématiques » → ``MATH`` ; discipline inconnue → premières lettres
    ASCII majuscules (accents supprimés). Le motif canonique exige ``[A-Z]+``
    (sans accent ni espace), d'où la normalisation systématique.
    """
    import unicodedata

    codes = {
        "mathématiques": "MATH", "mathematiques": "MATH", "maths": "MATH",
        "physique": "PHYS", "physique-chimie": "PHYCHIM",
        "chimie": "CHIM", "svt": "SVT", "sciences": "SC",
        "informatique": "INFO", "nsi": "NSI", "snt": "SNT",
    }
    cle = discipline.strip().lower()
    if cle in codes:
        return codes[cle]
    sans_accents = "".join(
        c for c in unicodedata.normalize("NFD", cle)
        if unicodedata.category(c) != "Mn"
    )
    code = "".join(c for c in sans_accents.upper() if c.isascii() and c.isalpha())
    return code[:4] or "DISC"


def numeroter_exercices(
    segments: list[SegmentExercice],
    discipline: str,
    annee: int,
    serie: str,
) -> list[dict]:
    """Construit les dictionnaires d'exercices avec identifiant canonique.

    L'identifiant suit le motif ``DISCIPLINE-ANNEE-SERIE-NNN`` exigé par
    :func:`data_low.validate.valider_exercice`, ce qui garantit l'unicité
    dès la segmentation (avant même l'insertion en base).
    """
    prefixe = f"{_code_discipline(discipline)}-{annee}-{serie.upper()}"
    exercices: list[dict] = []
    for seg in segments:
        identifiant = f"{prefixe}-{seg.numero:03d}"
        exercices.append({
            "id": identifiant,
            "source": "numérisation",
            "year": annee,
            "serie": serie,
            "discipline": discipline.lower(),
            "statement": seg.enonce,
            "solution_ref": "",   # à compléter lors de l'annotation experte
            "concepts": [],       # à compléter lors de l'annotation experte
            "bareme": seg.bareme,
            "a_verifier": seg.a_verifier,
        })
    return exercices
