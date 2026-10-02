# Pipeline Data-Low (étapes 01 à 07)

Chaîne de production du corpus Data-Low à partir des sujets scannés du
baccalauréat tchadien. Chaque étape lit la sortie de la précédente ; les
sorties intermédiaires restent dans le dossier de travail, seul le JSONL
final (étapes 05/06) est versionné.

| Étape | Fichier | Rôle | Dépendances |
|---|---|---|---|
| 01 | `01_scan.sh` | Nettoyage image + couche OCR invisible (pdfsandwich) | pdfsandwich, ImageMagick |
| 02 | `02_ocr.py` | OCR page par page à 300 dpi (Tesseract fra) | pdf2image, pytesseract |
| 03 | `03_postprocess.py` | Aplanissement du bruit OCR (espaces, NFC) | stdlib |
| 04 | `04_segment_exercises.py` | Découpe en exercices, schéma v2.0 (tableau 2.6) | stdlib |
| 05 | `05_build_full_dataset.py` | Enchaîne 01→04 sur une série complète, JSONL final | stdlib |
| 06 | `06_auto_enrich.py` | Pré-annotation concepts STEM / Bloom (aide, non définitive) | stdlib |
| 07 | `07_export_csv.py` | Feuille CSV de la campagne d'annotation | stdlib |

Exemple complet (série D) :

```bash
python pipeline/05_build_full_dataset.py \
    --pdf_dir sujets/sujets_math_serieD --series D \
    --processed_dir work/processed_D \
    --output data/full/exercises_D.jsonl
python pipeline/06_auto_enrich.py \
    --input data/full/exercises_D.jsonl \
    --output data/full/exercises_D.enriched.jsonl
python pipeline/07_export_csv.py \
    --input data/full/exercises_D.enriched.jsonl \
    --output campagne/dataset_D.csv
```

Validation du JSONL produit avant toute publication :

```bash
python -c "import sys; sys.path.insert(0, '../Low-Eval-Kit'); \
from loweval.ingest_corpus import lire_jsonl; \
print(len(lire_jsonl('data/full/exercises_D.enriched.jsonl')), 'exercices valides')"
```
