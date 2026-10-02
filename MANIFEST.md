# MANIFEST — Manifeste de reproductibilité de Data-Low (v2.0)

## 1. Identité du jeu de données

| Élément | Valeur verrouillée |
|---|---|
| Nom | Data-Low |
| Version du schéma | 2.0 (`schema_version`, const dans le schéma JSON) |
| Provenance | Sujets officiels du baccalauréat tchadien, séries C, D, E (mathématiques) |
| Identifiant canonique | `TCD-<MATIERE>-<ANNEE>-<SERIE>-<NN>` — jamais réutilisé |
| Licence | CC BY-NC 4.0 (sujets : propriété de l'État tchadien, usage recherche) |

## 2. Comment régénérer le corpus

Les seules entrées nécessaires sont les PDF scannés des sujets (non
redistribués dans ce dépôt — propriété de l'État tchadien ; les détenir
sous `sujets/`). Ensuite, par série :

```bash
# 1. OCR + segmentation + consolidation (JSONL v2)
python pipeline/05_build_full_dataset.py \
    --pdf_dir sujets/sujets_math_serieD --series D \
    --processed_dir work/processed_D \
    --output data/full/exercises_D.jsonl

# 2. Pré-annotation (aide à la saisie — ne remplace pas l'humain)
python pipeline/06_auto_enrich.py \
    --input data/full/exercises_D.jsonl \
    --output data/full/exercises_D.enriched.jsonl

# 3. Feuille de campagne d'annotation
python pipeline/07_export_csv.py \
    --input data/full/exercises_D.enriched.jsonl \
    --output campagne/dataset_D.csv
```

Environnement : Python ≥ 3.10, `pdfsandwich` + ImageMagick, `pdf2image`,
`pytesseract` avec le modèle `fra`. Les étapes 03 à 07 n'utilisent que la
bibliothèque standard.

## 3. Validation avant publication

Le JSONL produit doit passer la validation du schéma 2.0 avant tout dépôt :

```bash
python -c "import sys; sys.path.insert(0, '../Low-Eval-Kit'); \
from loweval.ingest_corpus import lire_jsonl; \
print(len(lire_jsonl('data/full/exercises_D.enriched.jsonl')), 'exercices valides')"
```

Tout exercice rejeté cite la ligne et le motif (champ manquant, famille
hors taxonomie, version future, identifiant dupliqué).

## 4. Paramètres d'annotation verrouillés

| Paramètre | Valeur | Source |
|---|---|---|
| Taille de l'échantillon double annotation | n = 150 | §4.4 |
| Seuil de convenance κ (Cohen) | 0,75 | §4.4 |
| κ mesuré famille visuo-spatiale | 0,74 (sous seuil) | figure 2.3 |
| Campagne | `double_annotation_2026` (figée) | annexe B |
| Étiquette finale | `arbitre = 1` uniquement | annexe B |
| Familles d'erreurs | 5 (référentiel `erreurs` ids 1–5) | tableau 2.4 |

## 5. Traçabilité

* Chaque modification d'un exercice met à jour `updated_at` (base annexe C)
  et est journalisée par commit Git sur `data/full/`.
* Les sorties intermédiaires du pipeline (OCR brut/nettoyé) restent dans le
  dossier de travail, exclues du dépôt (`.gitignore`), régénérables à volonté.
* Le hash SHA-256 du JSONL publié est reporté dans le dépôt Bench-Low à
  chaque campagne d'évaluation.

## 6. Checklist avant publication d'une version

- [ ] `lire_jsonl` valide le JSONL sans erreur (schéma 2.0).
- [ ] Aucun identifiant dupliqué (`identifiants_uniques`).
- [ ] Les annotations portent `arbitre` et la campagne `double_annotation_2026`.
- [ ] La mention d'incertitude visuo-spatiale figure dans la documentation.
- [ ] La licence CC BY-NC 4.0 est rappelée dans le README.
- [ ] Le hash SHA-256 du fichier publié est calculé et archivé.
