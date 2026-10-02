"""Complétude et cohérence des annotations Data-Low (section 2.4).

Deux responsabilités distinctes :

* :func:`completer_annotation_exercice` — pendant la phase d'annotation, on
  part d'un exercice collecté (énoncé, corrigé) et on y rattache la
  solution de référence et les concepts attendus issus de l'analyse du
  correcteur. L'opération est **non mutante** : le corpus source reste
  intact, seule la copie enrichie est versée dans la base.
* :func:`controler_annotations` — contrôle qualité avant versement : tout
  segment textuel annoté doit exister **dans la production de l'élève**.
  Seule exception : le type ``visuo-spatiale``, dont le segment désigne une
  zone d'une figure (p. ex. « figure 2, zone A ») et ne peut donc pas être
  retrouvé dans le texte de la copie.
"""

from __future__ import annotations

from typing import Any

from Low-Eval-Kit.errors import DonneeInvalideError

#: Type dont le segment référence une figure, non le texte de la production.
#: Aligné sur ``data_low.taxonomie.TYPES_ERREUR`` (seule valeur « visuelle »).
_TYPE_VISUEL = "visuo-spatiale"


def completer_annotation_exercice(exercice: dict[str, Any],
                                  solution: str,
                                  concepts: list[str]) -> dict[str, Any]:
    """Retourne une copie de l'exercice enrichie de la solution et des concepts.

    Lève :class:`DonneeInvalideError` si la solution est vide ou blanche :
    un exercice sans corrigé de référence ne peut alimenter ni l'annotation
    (pas de vérité terrain) ni le prompt (pas de référence de comparaison).
    L'entrée n'est jamais modifiée (les annotations humaines passent par
    ``data_low.qualite`` et la base SQLite, pas par cette fonction).
    """
    if not solution or not solution.strip():
        raise DonneeInvalideError(
            f"Exercice « {exercice.get('id', '?')} » : solution de référence "
            "vide — impossible de compléter l'annotation sans corrigé."
        )
    copie = dict(exercice)
    copie["solution_ref"] = solution
    copie["concepts"] = [str(c) for c in (concepts or [])]
    return copie


def controler_annotations(annotations: list[dict[str, Any]],
                          production: str) -> list[str]:
    """Vérifie que chaque segment annoté figure dans la production de l'élève.

    Retourne la liste des problèmes détectés (vide = contrôle passé). Un
    segment hors production signale une annotation défaillante — adresse de
    page fausse, OCR mal aligné, transcription approximative — qui serait
    pénalisée à tort lors de la mesure de Precision@k.

    La correspondance est tolérante aux espaces multiples et à la casse,
    car la production provient d'un OCR (bruit d'espacement fréquent).
    """
    def _normalise(texte: str) -> str:
        return " ".join(texte.lower().split())

    production_norm = _normalise(production or "")
    problemes = []
    for annotation in annotations or []:
        type_erreur = annotation.get("error_type", "")
        span = annotation.get("span")
        if not span:
            continue  # annotation sans segment : rien à localiser
        if type_erreur == _TYPE_VISUEL:
            continue  # segment figure/zone : hors du texte par nature
        if _normalise(str(span)) not in production_norm:
            problemes.append(
                f"[{type_erreur}] segment « {span} » absent de la production."
            )
    return problemes
