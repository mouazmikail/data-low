# -*- coding: utf-8 -*-
"""Étape 4 — Segmentation du texte OCR en exercices individuels (schéma v2.0).

Recherche les marqueurs « Exercice n » (chiffres ou numération romaine) dans
le texte continu du sujet, puis découpe chaque segment en un enregistrement
conforme au schéma Data-Low 2.0 (tableau 2.6 du manuscrit) :

    exercise_id, year, series, subject, source, statement, assets,
    reference_solution, stem_concepts, bloom_level, annotations

Correction majeure par rapport à l'ancien pipeline : les champs produits
étaient un format v1 maison (id, statement_text, domain, cognitive_level…)
incompatible avec le schéma du manuscrit ; l'identifiant est désormais
canonique « TCD-MATH-1995-C-01 » et les champs non remplis par l'automatique
(reference_solution, stem_concepts, bloom_level, annotations) sont initialisés
à des valeurs vides, en attente de la double annotation humaine (chapitre 2 §4).

Usage : python pipeline/04_segment_exercises.py --input ocr_clean.json \
          --year 1995 --series C --subject mathematiques --output_dir out/
"""

import argparse
import json
import re
from pathlib import Path

# Marqueurs d'exercice tolérés : « Exercice 3 », « EXERCICE II », etc.
# re.IGNORECASE couvre les variantes de casse rencontrées dans les archives.
MARQUEUR_EXERCICE = re.compile(
    r"(Exercice\s+\d+|EXERCICE\s+\d+|Exercice\s+[IVX]+)",
    re.IGNORECASE,
)

# Série du baccalauréat tchadien couverte par le corpus (annexe C).
SERIES_VALIDES = ("C", "D", "E")

# Codes matière utilisés dans l'identifiant canonique (TCD-MATH-1995-C-01).
CODES_MATIERE = {"mathematiques": "MATH", "physique": "PHYS", "svt": "SVT",
                 "informatique": "SNT"}


def segmenter_exercices(pages: list[dict]) -> list[dict]:
    """Découpe le texte des pages en segments d'exercices numérotés.

    Concatène le texte de toutes les pages, repère chaque marqueur
    « Exercice n » et affecte à chaque marqueur le texte compris entre lui et
    le marqueur suivant (ou la fin du document). Retourne une liste de
    {"exercise_num": str, "statement": str} dans l'ordre du sujet.
    """
    texte_global = "\n".join(page["text"] for page in pages)
    marqueurs = list(MARQUEUR_EXERCICE.finditer(texte_global))
    segments = []

    for position, marqueur in enumerate(marqueurs):
        debut = marqueur.start()
        # Fin du segment : début du marqueur suivant, ou fin du document.
        fin = marqueurs[position + 1].start() if position + 1 < len(marqueurs) \
            else len(texte_global)
        contenu = texte_global[debut:fin].strip()

        # Numéro affiché de l'exercice (chiffres arabes ou romains).
        num_trouve = re.search(r"\d+|[IVX]+", marqueur.group())
        numero = num_trouve.group() if num_trouve else str(position + 1)
        segments.append({"exercise_num": numero, "statement": contenu})

    return segments


def construire_exercice(annee: int, serie: str, sujet: str,
                        segment: dict, rang: int) -> dict:
    """Construit un enregistrement v2.0 complet à partir d'un segment OCR.

    `rang` est la position 1-based du segment dans le sujet : elle sert à
    numéroter l'identifiant canonique « TCD-MATH-1995-C-01 » (le numéro
    affiché dans le sujet, en romain par exemple, n'est pas fiable).
    """
    return {
        # Identifiant canonique : source-matière-année-série-numéro séquentiel.
        "exercise_id": f"TCD-{CODES_MATIERE.get(sujet, sujet.upper()[:4])}-{annee}-{serie}-{rang:02d}",
        "year": annee,                  # année de la session d'examen
        "series": serie,                # série du bac (C, D ou E)
        "subject": sujet,               # matière (mathematiques, physique…)
        "source": "archive_officielle", # provenance documentée (tableau 2.6)
        "statement": segment["statement"],  # énoncé OCR (nettoyé, étape 3)
        "assets": [],                   # figures associées (à renseigner)
        "reference_solution": "",       # corrigé de référence (annotation)
        "stem_concepts": [],            # concepts STEM (annotation/étape 06)
        "bloom_level": "",              # taxonomie de Bloom (annotation)
        "annotations": [],              # erreurs annotées (double annotation)
        "schema_version": "2.0",        # version du format (verrouillée)
    }


def main() -> None:
    """Point d'entrée CLI : segmente un sujet et écrit un JSON par exercice."""
    analyseur = argparse.ArgumentParser(description="Segmentation en exercices (schéma v2).")
    analyseur.add_argument("--input", required=True, help="JSON OCR nettoyé (étape 3)")
    analyseur.add_argument("--year", required=True, type=int, help="Année de session")
    analyseur.add_argument("--series", required=True, choices=SERIES_VALIDES)
    analyseur.add_argument("--subject", default="mathematiques", help="Matière")
    analyseur.add_argument("--output_dir", required=True, help="Dossier de sortie")
    arguments = analyseur.parse_args()

    with open(arguments.input, encoding="utf-8") as flux:
        pages = json.load(flux)

    segments = segmenter_exercices(pages)
    dossier_sortie = Path(arguments.output_dir)
    dossier_sortie.mkdir(parents=True, exist_ok=True)

    # Un fichier JSON par exercice : reprise fine possible exercice par
    # exercice si un segment doit être corrigé à la main.
    for rang, segment in enumerate(segments, start=1):
        exercice = construire_exercice(arguments.year, arguments.series,
                                       arguments.subject, segment, rang)
        chemin = dossier_sortie / f"{exercice['exercise_id']}.json"
        with open(chemin, "w", encoding="utf-8") as flux:
            json.dump(exercice, flux, ensure_ascii=False, indent=2)

    print(f"{len(segments)} exercice(s) généré(s) dans {dossier_sortie}")


if __name__ == "__main__":
    main()
