# -*- coding: utf-8 -*-
"""Étape 2 — OCR page par page d'un PDF nettoyé (étape 1).

Lit le PDF « sandwich » produit par 01_scan.sh, rasterise chaque page à
300 dpi et en extrait le texte avec Tesseract (français). Le résultat est
un JSON structuré par page, conservation brute du texte OCR : aucune
correction n'est appliquée ici (l'étape 03 fait le nettoyage).

Usage : python pipeline/02_ocr.py --input cleaned.pdf --output ocr_raw.json
"""

import argparse
import json
import unicodedata
from pathlib import Path


def normaliser_unicode(texte: str) -> str:
    """Normalise le texte en NFC (forme canonique combinée).

    Les PDF scannés mélangent souvent les formes Unicode (caractères + accents
    décomposés). La NFC garantit qu'un même caractère a toujours la même
    séquence d'octets, condition de la déduplication et des regex stables.
    """
    return unicodedata.normalize("NFC", texte)


def ocr_pdf(chemin_pdf: str, dpi: int = 300) -> list[dict]:
    """Rasterise le PDF et OCR-ise chaque page avec Tesseract (fra).

    Retourne une liste de {"page": n, "text": ...} indexée à partir de 1.
    Les imports lourds (pdf2image, pytesseract) sont faits à l'appel pour
    que --help reste utilisable sans les dépendances installées.
    """
    from pdf2image import convert_from_path      # rasterisation PDF -> images
    import pytesseract                          # interface Tesseract

    pages = convert_from_path(chemin_pdf, dpi=dpi)
    resultats = []
    for numero, image in enumerate(pages, start=1):
        texte = pytesseract.image_to_string(image, lang="fra")
        resultats.append({"page": numero, "text": normaliser_unicode(texte)})
    return resultats


def main() -> None:
    """Point d'entrée CLI de l'étape 2."""
    analyseur = argparse.ArgumentParser(description="OCR page par page (Tesseract, fra).")
    analyseur.add_argument("--input", required=True, help="PDF nettoyé (étape 1)")
    analyseur.add_argument("--output", required=True, help="JSON brut des pages OCR")
    arguments = analyseur.parse_args()

    resultats = ocr_pdf(arguments.input)

    # Création des répertoires parents si besoin, puis écriture UTF-8.
    Path(arguments.output).parent.mkdir(parents=True, exist_ok=True)
    with open(arguments.output, "w", encoding="utf-8") as flux:
        json.dump(resultats, flux, ensure_ascii=False, indent=2)

    print(f"{len(resultats)} page(s) OCR-isée(s) -> {arguments.output}")


if __name__ == "__main__":
    main()
