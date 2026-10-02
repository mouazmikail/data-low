"""Validation et export des exercices du corpus Data-Low.

Chaque exercice qui entre dans la base doit passer la validation
:func:`valider_exercice` : identifiant unique bien formé, énoncé et
solution de référence non vides, liste de concepts déclarée, et — pour
les exercices issus d'une numérisation — mention de la source. Les
erreurs sont regroupées dans :class:`RapportValidation` plutôt que
levées une par une, afin de produire un rapport d'erreur exploitable
lors de la phase de numérisation en masse.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 1. Exigences minimales sur un exercice
# ---------------------------------------------------------------------------
#: Identifiant canonique : DISCIPLINE-ANNEE-SERIE-NNN (ex. MATH-2023-SN-012).
_MOTIF_ID = re.compile(r"^[A-Z]+-\d{4}-[A-Z0-9]+-\d{3,4}$")

#: Champs obligatoires, indépendamment du mode de collecte.
CHAMPS_OBLIGATOIRES = ("id", "discipline", "statement", "solution_ref", "concepts")


@dataclass
class RapportValidation:
    """Bilan d'une passe de validation sur un lot d'exercices.

    ``erreurs`` associe l'identifiant d'un exercice à la liste des
    problèmes détectés ; un exercice absent de ce dictionnaire est valide.
    """

    total: int = 0
    valides: int = 0
    erreurs: dict[str, list[str]] = field(default_factory=dict)

    def ajouter_erreur(self, identifiant: str, probleme: str) -> None:
        self.erreurs.setdefault(identifiant or "<sans-id>", []).append(probleme)


def valider_exercice(exercice: dict[str, Any]) -> list[str]:
    """Retourne la liste des problèmes d'un exercice (vide = valide).

    Règles :
      * tous les champs obligatoires présents et non vides ;
      * ``id`` conforme au motif canonique (garantit l'unicité dans la base) ;
      * ``concepts`` : liste non vide (concepts STEM attendus, section 2.5) ;
      * ``images`` : si présent, doit être une liste JSON-sérialisable.
    """
    problemes: list[str] = []
    identifiant = str(exercice.get("id", ""))

    # 1. Champs obligatoires non vides.
    for champ in CHAMPS_OBLIGATOIRES:
        if not exercice.get(champ):
            problemes.append(f"champ obligatoire manquant ou vide : {champ}")

    # 2. Forme de l'identifiant (quand il existe).
    if identifiant and not _MOTIF_ID.match(identifiant):
        problemes.append(
            f"identifiant « {identifiant} » non conforme au motif "
            "DISCIPLINE-ANNEE-SERIE-NNN"
        )

    # 3. Concepts : liste non vide.
    concepts = exercice.get("concepts")
    if concepts is not None and (not isinstance(concepts, list) or not concepts):
        problemes.append("« concepts » doit être une liste non vide")

    # 4. Images : liste de chemins sérialisables en JSON (facultatif).
    images = exercice.get("images")
    if images is not None and (
        not isinstance(images, list) or not all(isinstance(i, str) for i in images)
    ):
        problemes.append("« images » doit être une liste de chemins (str)")

    return problemes


def valider_corpus(exercices: list[dict[str, Any]]) -> RapportValidation:
    """Valide un lot d'exercices et lève une erreur s'il y a des doublons d'identifiant.

    La duplication d'identifiant est une faute de construction du corpus :
    elle ne peut pas être corrigée automatiquement, donc elle lève
    :class:`loweval.errors.DonneeInvalideError` avec la liste des doublons.
    """
    from Low-Eval-Kit.errors import DonneeInvalideError

    rapport = RapportValidation(total=len(exercices))
    vus: dict[str, int] = {}
    for ex in exercices:
        identifiant = str(ex.get("id", ""))
        vus[identifiant] = vus.get(identifiant, 0) + 1
        problemes = valider_exercice(ex)
        if problemes:
            for p in problemes:
                rapport.ajouter_erreur(identifiant, p)
        else:
            rapport.valides += 1

    doublons = sorted(i for i, n in vus.items() if n > 1 and i)
    if doublons:
        raise DonneeInvalideError(
            "Identifiants dupliqués dans le corpus : " + ", ".join(doublons)
        )
    return rapport


def exporter_jsonl(exercices: list[dict[str, Any]], chemin: Path | str) -> int:
    """Exporte les exercices validés au format JSONL (une ligne = un exercice).

    Le JSONL est le format pivot du corpus : il alimente d'un côté la base
    SQLite (via :func:`loweval.db.charger_jsonl`) et de l'autre les corpus
    d'entraînement ou d'évaluation externes.

    :return: nombre d'exercices écrits.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as flux:
        for ex in exercices:
            # Normalisation : les images et concepts restent des listes dans
            # le JSONL (la base les stocke sérialisés) pour faciliter la
            # relecture humaine.
            flux.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return len(exercices)
