#!/usr/bin/env bash
# =============================================================================
# Étape 1 — Nettoyage et OCR en couche (pdfsandwich) d'un sujet scanné.
#
# pdfsandwich redresse (deskew) et normalise l'image, puis injecte une couche
# de texte invisible : le PDF reste visuellement identique mais devient
# sélectionnable/recherchable, ce que l'étape 02 exploite.
#
# Usage : bash pipeline/01_scan.sh <entrée.pdf> <sortie.pdf>
# =============================================================================
set -euo pipefail

# Fichier d'entrée (scan brut) et fichier de sortie (PDF sandwich).
INPUT_PDF="${1:?Usage : 01_scan.sh <entrée.pdf> <sortie.pdf>}"
OUTPUT_PDF="${2:?Usage : 01_scan.sh <entrée.pdf> <sortie.pdf>}"

# Vérification de la présence de l'outil avant tout traitement.
command -v pdfsandwich >/dev/null 2>&1 || {
    echo "ERREUR : pdfsandwich est requis (apt install pdfsandwich)." >&2
    exit 1
}

# -lang fra      : modèle de langue français (Tesseract).
# -resolution 300: densité standard d'archivage, bon compromis qualité/taille.
# -coo           : options ImageMagick appliquées avant l'OCR (redressement
#                  jusqu'à 40 %, normalisation du contraste).
pdfsandwich \
  -lang fra \
  -resolution 300 \
  -coo "-deskew 40% -normalize" \
  -o "$OUTPUT_PDF" \
  "$INPUT_PDF"

echo "Étape 1 terminée : $OUTPUT_PDF"
