# -*- coding: utf-8 -*-
"""Étape 7 — Export JSONL vers CSV pour la campagne d'annotation.

Produit la feuille de travail distribuée aux annotateurs : une ligne par
exercice, les listes JSON (assets, stem_concepts, annotations) aplaties en
texte séparé par « | », les champs d'annotation laissés vides pour saisie.

Correction par rapport à l'ancien « 1.py » : chemins en dur supprimés,
colonnes fixées par le schéma v2 (plus de dépendance à l'ordre des clés du
premier enregistrement), sortie UTF-8 avec BOM (Excel français).

Usage : python pipeline/07_export_csv.py --input data/full/exercises_D.jsonl \
          --output campagne/dataset_D.csv
"""

import argparse
import csv
import json

# Colonnes dans l'ordre de saisie de la feuille d'annotation. Les champs
# « annot_* » sont remplis à la main par les annotateurs puis réimportés
# dans le schéma JSON par la moulinette de la double annotation.
COLONNES = [
    "exercise_id", "year", "series", "subject", "statement",
    "reference_solution", "stem_concepts", "bloom_level",
    "annot_error_type", "annot_location", "annot_diagnostic",
]


def aplatir(valeur) -> str:
    """Aplati une valeur JSON pour le CSV : listes jointes par « | », le reste en texte."""
    if isinstance(valeur, list):
        return "|".join(str(element) for element in valeur)
    if valeur is None:
        return ""
    return str(valeur)


def main() -> None:
    """Point d'entrée CLI : convertit un JSONL v2 en CSV de campagne."""
    analyseur = argparse.ArgumentParser(description="Export JSONL v2 -> CSV d'annotation.")
    analyseur.add_argument("--input", required=True, help="JSONL d'entrée")
    analyseur.add_argument("--output", required=True, help="CSV de sortie")
    arguments = analyseur.parse_args()

    compteur = 0
    # utf-8-sig : BOM UTF-8 pour qu'Excel (Windows, locale française) ouvre
    # correctement les accents.
    with open(arguments.output, "w", encoding="utf-8-sig", newline="") as flux_csv:
        redacteur = csv.DictWriter(flux_csv, fieldnames=COLONNES)
        redacteur.writeheader()
        with open(arguments.input, encoding="utf-8") as flux_jsonl:
            for ligne in flux_jsonl:
                ligne = ligne.strip()
                if not ligne:
                    continue
                exercice = json.loads(ligne)
                redacteur.writerow({
                    "exercise_id": exercice.get("exercise_id", ""),
                    "year": exercice.get("year", ""),
                    "series": exercice.get("series", ""),
                    "subject": exercice.get("subject", ""),
                    "statement": exercice.get("statement", ""),
                    "reference_solution": exercice.get("reference_solution", ""),
                    "stem_concepts": aplatir(exercice.get("stem_concepts", [])),
                    "bloom_level": exercice.get("bloom_level", ""),
                    # Champs de saisie annotateur : initialisés vides.
                    "annot_error_type": "",
                    "annot_location": "",
                    "annot_diagnostic": "",
                })
                compteur += 1

    print(f"Export terminé : {compteur} exercice(s) -> {arguments.output}")


if __name__ == "__main__":
    main()
