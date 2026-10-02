# -*- coding: utf-8 -*-
"""Étape 5 — Chaîne complète de construction du corpus par série.

Enchaîne les étapes 1 à 04 pour chaque sujet PDF d'une série, puis consolide
tous les exercices segmentés en un unique fichier JSONL conforme au schéma
Data-Low 2.0 : c'est ce fichier qui est versionné et publié (dépôt Data-Low).

Correction majeure par rapport à l'ancien script : chemins codés en dur
et série D figée ; tout est désormais passé en arguments, l'interpréteur
Python courant est utilisé (portabilité des environnements virtuels) et la
sortie est du JSONL (une ligne par exercice), format attendu par le
Low-Eval Kit (`scripts/ingest_data_low.py`).

Usage : python pipeline/05_build_full_dataset.py \
          --pdf_dir sujets/sujets_math_serieD --series D \
          --processed_dir work/processed_D --output data/full/exercises_D.jsonl
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Répertoire racine du dépôt, résolu une fois pour lancer les sous-étapes
# avec des chemins absolus (le script est relançable depuis n'importe où).
RACINE = Path(__file__).resolve().parent.parent


def extraire_annee(nom_fichier: str) -> int | None:
    """Extrait l'année d'un nom de fichier de sujet (ex. « Bac-D-1998.pdf »)."""
    match = re.search(r"(19\d{2}|20\d{2})", nom_fichier)
    return int(match.group()) if match else None


def traiter_sujet(pdf: Path, annee: int, serie: str, sujet: str,
                  dossier_travail: Path) -> list[dict]:
    """Enchaîne les étapes 01 à 04 sur un sujet PDF ; retourne ses exercices."""
    dossier_annee = dossier_travail / str(annee)
    dossier_annee.mkdir(parents=True, exist_ok=True)

    pdf_nettoye = dossier_annee / "cleaned.pdf"
    json_brut = dossier_annee / "ocr_raw.json"
    json_nettoye = dossier_annee / "ocr_clean.json"
    dossier_exercices = dossier_annee / "exercises"

    # Étape 1 : nettoyage + couche OCR invisible (pdfsandwich).
    subprocess.run(
        ["bash", str(RACINE / "pipeline" / "01_scan.sh"),
         str(pdf), str(pdf_nettoye)],
        check=True,
    )
    # Étape 2 : OCR page par page (raster 300 dpi + Tesseract fra).
    subprocess.run(
        [sys.executable, str(RACINE / "pipeline" / "02_ocr.py"),
         "--input", str(pdf_nettoye), "--output", str(json_brut)],
        check=True,
    )
    # Étape 3 : nettoyage du texte OCR.
    subprocess.run(
        [sys.executable, str(RACINE / "pipeline" / "03_postprocess.py"),
         str(json_brut), str(json_nettoye)],
        check=True,
    )
    # Étape 4 : segmentation en exercices v2.0.
    subprocess.run(
        [sys.executable, str(RACINE / "pipeline" / "04_segment_exercises.py"),
         "--input", str(json_nettoye), "--year", str(annee),
         "--series", serie, "--subject", sujet,
         "--output_dir", str(dossier_exercices)],
        check=True,
    )

    # Collecte des exercices segmentés pour cette année.
    exercices = []
    for fichier in sorted(dossier_exercices.glob("*.json")):
        with open(fichier, encoding="utf-8") as flux:
            exercices.append(json.load(flux))
    return exercices


def main() -> None:
    """Point d'entrée CLI : traite toute une série et écrit le JSONL final."""
    analyseur = argparse.ArgumentParser(description="Construction du corpus JSONL (schéma v2).")
    analyseur.add_argument("--pdf_dir", required=True, help="Dossier des sujets PDF")
    analyseur.add_argument("--series", required=True, choices=("C", "D", "E"))
    analyseur.add_argument("--subject", default="mathematiques", help="Matière")
    analyseur.add_argument("--processed_dir", required=True, help="Dossier de travail")
    analyseur.add_argument("--output", required=True, help="JSONL de sortie")
    arguments = analyseur.parse_args()

    dossier_pdf = Path(arguments.pdf_dir)
    tous_les_exercices: list[dict] = []

    # Les PDF sont traités par année croissante : l'ordre du JSONL final est
    # déterministe (condition de reproductibilité, MANIFEST.md).
    for pdf in sorted(dossier_pdf.glob("*.pdf")):
        annee = extraire_annee(pdf.name)
        if annee is None:
            print(f"⚠ Année indétectable, sujet ignoré : {pdf.name}")
            continue
        print(f"Traitement de l'année {annee} ({pdf.name})…")
        tous_les_exercices.extend(
            traiter_sujet(pdf, annee, arguments.series, arguments.subject,
                          Path(arguments.processed_dir))
        )

    # Écriture du JSONL : une ligne JSON complète par exercice.
    chemin_sortie = Path(arguments.output)
    chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin_sortie, "w", encoding="utf-8") as flux:
        for exercice in tous_les_exercices:
            flux.write(json.dumps(exercice, ensure_ascii=False) + "\n")

    print(f"Corpus généré : {len(tous_les_exercices)} exercice(s) -> {chemin_sortie}")


if __name__ == "__main__":
    main()
