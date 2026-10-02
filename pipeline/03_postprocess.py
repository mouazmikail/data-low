# -*- coding: utf-8 -*-
"""Étape 3 — Nettoyage du texte OCR brut.

Le bruit typique du Tesseract sur scans d'archives (sauts de ligne intempestifs,
espaces multiples, caractères fantômes) est aplani ici, avant la segmentation :
les regex de l'étape 04 supposent un texte « au propre ».

Usage : python pipeline/03_postprocess.py <ocr_raw.json> <ocr_clean.json>
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path


def nettoyer_texte(texte: str) -> str:
    """Aplani un texte OCR : NFC, retours à la ligne en espaces, compactage.

    Les retours à la ligne ne portent aucune information sémantique dans les
    sujets d'examen (coupe de mots en fin de ligne) : les remplacer par un
    espace simple puis compactage des espaces multiples suffit.
    """
    texte = unicodedata.normalize("NFC", texte)
    texte = re.sub(r"\s+", " ", texte)   # espaces/retours multiples -> un seul
    return texte.strip()


def main() -> None:
    """Point d'entrée CLI : lit le JSON brut et réécrit chaque page nettoyée."""
    analyseur = argparse.ArgumentParser(description="Nettoyage du texte OCR brut.")
    analyseur.add_argument("entree", help="JSON OCR brut (étape 2)")
    analyseur.add_argument("sortie", help="JSON OCR nettoyé")
    arguments = analyseur.parse_args()

    with open(arguments.entree, encoding="utf-8") as flux:
        pages = json.load(flux)

    # Nettoyage en place, page par page ; la structure {"page", "text"} est
    # conservée à l'identique pour ne pas casser l'étape 04.
    for page in pages:
        page["text"] = nettoyer_texte(page["text"])

    Path(arguments.sortie).parent.mkdir(parents=True, exist_ok=True)
    with open(arguments.sortie, "w", encoding="utf-8") as flux:
        json.dump(pages, flux, ensure_ascii=False, indent=2)

    print(f"{len(pages)} page(s) nettoyée(s) -> {arguments.sortie}")


if __name__ == "__main__":
    main()
