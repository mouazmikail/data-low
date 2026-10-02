"""Collecte des sources et conversion vers le schéma canonique Data-Low (§2.5).

Étape 1 du pipeline de construction (``scripts/build_data_low.py``). Le
« dossier de sources » contient des fichiers hétérogènes ; ce module les
ramène tous au même dictionnaire d'exercice :

* ``.json``  — export structuré (liste d'objets), p. ex. le dépôt
  Data-Low tchadien ``dataset_all_exercises_{C,D}.json`` ; les champs sont
  translittérés vers le schéma canonique (``statement_text`` →
  ``statement``, ``subthemes``/``tags`` → ``concepts``…) ;
* ``.jsonl`` — corpus au format canonique (un exercice par ligne) ;
* ``.pdf`` / images (``.png``, ``.jpg``, ``.tiff``) — sujets numérisés :
  OCR contrôlée à deux moteurs (``data_low.ocr``), puis segmentation en
  exercices numérotés canoniquement (``data_low.segment``).

Deux garde-fous de qualité :

* toute page dont les deux moteurs d'OCR divergent (similarité < 0,90)
  est marquée ``ocr_a_relire`` et **exclue du corpus** par
  :func:`corpus_valide` tant qu'un humain ne l'a pas relue ;
* chaque exercice structuré est contrôlé par ``valider_exercice`` ; les
  avertissements alimentent le rapport de construction.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from data_low.ocr import ocr_controle
from data_low.segment import numeroter_exercices, segmenter_sujet
from data_low.validate import valider_exercice

logger = logging.getLogger("loweval.data_low.ingest")

#: Extensions traitées comme des sources textuelles structurées (pas d'OCR).
_EXTENSIONS_STRUCTUREES = {".json", ".jsonl"}
#: Extensions traitées comme des sujets numérisés (OCR contrôlée).
_EXTENSIONS_SCAN = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

#: Correspondance champs sources tchadiennes → schéma canonique Data-Low.
#: Les champs absents du fichier (p. ex. solution de référence non publiée)
#: reçoivent une valeur vide, complétée lors de l'annotation experte.
_TRANSLITERATION_CHAMPS = {
    "statement": "statement_text",
    "year": "year",
    "session": "session",
    "points": "points",
}


@dataclass
class RapportCollecte:
    """Bilan d'une passe de collecte sur un dossier de sources.

    Attributes:
        total: nombre d'exercices candidats (avant filtrage OCR) ;
        valides: exercices sans aucun avertissement de validation ;
        erreurs: messages d'avertissement par exercice (validation
            syntaxique, champs manquants) — le détail reste exploitable
            par le rapport de construction.
    """

    total: int = 0
    valides: int = 0
    erreurs: list[str] = field(default_factory=list)


def _translitterer_enregistrement(enregistrement: dict[str, Any],
                                  source: str,
                                  discipline: str,
                                  annee: int | None,
                                  serie: str | None) -> dict[str, Any]:
    """Convertit un enregistrement source vers le schéma canonique.

    La solution de référence (``solution_ref`` / ``correction``) et les
    concepts (``subthemes`` ou ``tags`` ou ``domain``) sont repris tels
    quels quand ils existent ; sinon on laisse champs vides, à compléter
    par l'annotation experte (``data_low.annotate``). L'identifiant source
    est conservé s'il est déjà canonique (la validation le signalerait
    sinon) ; les métadonnées d'origine restent dans ``notes``.
    """
    exercice: dict[str, Any] = {
        "id": str(enregistrement.get("id", "")),
        "source": source,
        "year": enregistrement.get("year", annee),
        # « serie » = série du bac (C/D/SN…) ; « session » (S1/S2) est une
        # information distincte, conservée telle quelle plus bas. Sans série
        # explicite dans l'enregistrement, on laisse vide : c'est le nom du
        # fichier (C/D) ou l'argument --serie qui tranchera ensuite.
        "serie": enregistrement.get("serie"),
        "discipline": enregistrement.get("discipline", discipline),
        "statement": enregistrement.get("statement_text")
        or enregistrement.get("statement") or "",
        "solution_ref": (enregistrement.get("solution_ref")
                         or enregistrement.get("correction") or ""),
        "concepts": (enregistrement.get("concepts")
                     or enregistrement.get("subthemes")
                     or enregistrement.get("tags")
                     or ([enregistrement["domain"]]
                         if enregistrement.get("domain") else [])),
    }
    if enregistrement.get("session"):
        exercice["session"] = enregistrement["session"]
    if enregistrement.get("images"):
        exercice["images"] = enregistrement["images"]
    if enregistrement.get("points") is not None:
        exercice["points"] = enregistrement["points"]
    if enregistrement.get("notes"):
        exercice["notes"] = enregistrement["notes"]
    return exercice


def _serie_depuis_nom(fichier: Path) -> str | None:
    """Devine la série du bac depuis le nom du fichier source.

    Ex. ``dataset_all_exercises_C.json`` → ``"C"`` ; ``sujet_2023_D.pdf`` →
    ``"D"``. Retourne ``None`` si aucune indication (l'appelant utilise
    alors la série passée en argument).
    """
    import re

    motif = re.search(r"(?:^|[_\-.])([CD])(?:[_\-.]|$)", fichier.stem,
                      flags=re.IGNORECASE)
    return motif.group(1).upper() if motif else None


def _canoniser_identifiants(exercices: list[dict[str, Any]],
                            discipline: str,
                            serie: str) -> None:
    """Renomme les identifiants non canoniques au motif DISCIPLINE-ANNEE-SERIE-NNN.

    Les exports bruts du terrain utilisent des identifiants propres à leur
    outil (p. ex. « TD_S_1990_S1_E2 ») qui violent le motif canonique exigé
    par la validation (§2.5). On conserve l'identifiant d'origine dans
    ``id_source`` (traçabilité de la collecte) et on numérote séquentiellement
    dans le fichier : l'unicité est garantie par la clé primaire SQLite.
    """
    import re

    from data_low.segment import _code_discipline

    motif_canonique = re.compile(r"^[A-Z]+-\d{4}-[A-Z0-9]+-\d{3,4}$")
    code = _code_discipline(discipline)
    for position, exercice in enumerate(exercices, start=1):
        identifiant = str(exercice.get("id", ""))
        if identifiant and motif_canonique.match(identifiant):
            continue  # déjà canonique : on ne touche à rien
        annee = exercice.get("year") or "XXXX"
        identifiant_source = identifiant or f"{exercice.get('source')}#{position}"
        exercice["id"] = f"{code}-{annee}-{serie}-{position:03d}"
        exercice["id_source"] = identifiant_source


def _lire_structures(chemin: Path, discipline: str, annee: int | None,
                     serie: str | None) -> list[dict[str, Any]]:
    """Lit un fichier JSON (liste) ou JSONL (lignes) et translittère."""
    exercices = []
    if chemin.suffix.lower() == ".json":
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        if not isinstance(donnees, list):
            raise ValueError(f"{chemin.name} : JSON attendu sous forme de liste.")
        enregistrements = donnees
    else:  # .jsonl
        enregistrements = [json.loads(l) for l in
                           chemin.read_text(encoding="utf-8").splitlines()
                           if l.strip()]
    for enregistrement in enregistrements:
        if isinstance(enregistrement, dict):
            exercices.append(_translitterer_enregistrement(
                enregistrement, chemin.name, discipline, annee, serie))
    # La série du bac se devine d'abord dans le nom du fichier (C/D),
    # faute de quoi on retombe sur l'argument --serie.
    serie_retenue = _serie_depuis_nom(chemin) or serie or "SN"
    _canoniser_identifiants(exercices, discipline, serie_retenue)
    for exercice in exercices:
        exercice["serie"] = exercice.get("serie") or serie_retenue
    return exercices


def _numeriser(chemin: Path, discipline: str, annee: int,
               serie: str) -> tuple[list[dict[str, Any]], bool]:
    """OCR contrôlée + segmentation d'un sujet numérisé.

    Retourne ``(exercices, a_relire)`` : quand les deux moteurs d'OCR
    divergent, tous les exercices de la page portent le drapeau
    ``ocr_a_relire`` et seront exclus par :func:`corpus_valide`.
    """
    page = ocr_controle(chemin)
    segments = segmenter_sujet(page.texte)
    exercices = numeroter_exercices(segments, discipline, annee, serie)
    for exercice in exercices:
        exercice["source"] = f"{chemin.name} (p. {page.page})"
    return exercices, page.a_relire


def collecter_sources(dossier: str | Path, discipline: str,
                      annee: int | None, serie: str | None,
                      ) -> tuple[list[dict[str, Any]], RapportCollecte]:
    """Collecte tous les exercices d'un dossier de sources hétérogène.

    Parcourt récursivement ``dossier`` ; chaque fichier est routé selon son
    extension (structuré → translittération, scan → OCR + segmentation).
    Chaque exercice reçoit le drapeau ``ocr_a_relire`` (faux pour les
    sources structurées) et est contrôlé par ``valider_exercice`` ; les
    avertissements alimentent le rapport retourné.
    """
    dossier = Path(dossier)
    if not dossier.is_dir():
        raise FileNotFoundError(f"Dossier de sources introuvable : {dossier}")

    exercices: list[dict[str, Any]] = []
    rapport = RapportCollecte()

    for chemin in sorted(dossier.rglob("*")):
        if not chemin.is_file():
            continue
        extension = chemin.suffix.lower()
        try:
            if extension in _EXTENSIONS_STRUCTUREES:
                lus = _lire_structures(chemin, discipline, annee, serie)
                for exercice in lus:
                    exercice.setdefault("ocr_a_relire", False)
                exercices.extend(lus)
            elif extension in _EXTENSIONS_SCAN:
                if annee is None or not serie:
                    raise ValueError(
                        "Sources numérisées (OCR) : --annee et --serie sont "
                        "requis pour numéroter les exercices canoniquement."
                    )
                numerises, a_relire = _numeriser(chemin, discipline,
                                                 annee, serie)
                for exercice in numerises:
                    exercice["ocr_a_relire"] = a_relire
                exercices.extend(numerises)
            else:
                logger.info("Extension ignorée : %s", chemin.name)
        except Exception as exc:  # une source défaillante n'arrête pas le lot
            rapport.erreurs.append(f"{chemin.name} : {type(exc).__name__} : {exc}")
            logger.warning("Source écartée %s : %s", chemin.name, exc)

    # -- contrôle syntaxique de chaque exercice collecté --------------------
    for exercice in exercices:
        rapport.total += 1
        problemes = valider_exercice(exercice)
        if problemes:
            rapport.erreurs.extend(
                f"{exercice.get('id', '?')} : {p}" for p in problemes)
        else:
            rapport.valides += 1
    return exercices, rapport


def corpus_valide(exercices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtre le corpus : exclut pages OCR à relire et énoncés vides.

    Un exercice marqué ``ocr_a_relire`` n'a pas sa place dans un corpus
    d'évaluation tant qu'un humain n'a pas tranché la divergence des deux
    moteurs (section 2.5 : « la qualité prime sur la quantité »).
    """
    return [ex for ex in exercices
            if not ex.get("ocr_a_relire") and (ex.get("statement") or "").strip()]
