# Data-Low — corpus annoté des sujets du baccalauréat tchadien (v2.0)

Corpus de production des chapitres 2 à 4 du manuscrit « Frugal Multimodal
Alignment » (M. Mikail, CY Cergy Paris Université) : sujets scannés de
mathématiques (séries C, D, E), OCR contrôlé, exercices segmentés et
annotés selon la taxonomie des cinq familles d'erreurs (tableau 2.4).

## Contenu du dépôt

```
schema/
  data_low.schema.json   Schéma JSON v2.0 (tableau 2.6) avec alias v1 documentés
  schema.sql             Schéma SQLite (annexe C) : exercises, erreurs, annotations
pipeline/
  01_scan.sh … 07_export_csv.py   Chaîne de production (voir pipeline/readme.md)
sql/
  parts_taxonomie_erreurs.sql       Parts des familles (annexe B, arbitre = 1)
  cas_visuospatiaux_discordants.sql Items à ré-arbitrer (κ = 0,74)
guidelines/
  annotation_guide.md    Guide de la double annotation (n = 150, κ ≥ 0,75)
data/
  sample/exercises.sample.jsonl     Échantillon conforme au schéma v2.0
  full/                  Corpus complet (JSONL versionné, à compléter)
MANIFEST.md              Manifeste de reproductibilité
LICENSE                  CC BY-NC 4.0
```

## Format v2.0 (tableau 2.6)

Un exercice = un objet JSON par ligne (JSONL) :

```json
{
  "exercise_id": "TCD-MATH-1995-C-01",
  "year": 1995, "series": "C", "subject": "mathematiques",
  "source": "archive_officielle",
  "statement": "Résoudre 2x + 4 = 10.",
  "assets": [],
  "reference_solution": "x = 3.",
  "stem_concepts": ["equation premier degre"],
  "bloom_level": "appliquer",
  "annotations": [
    {"error_type": "calculatoire", "location": "ligne 2",
     "diagnostic": "erreur de signe", "annotator": "expert_1", "arbitre": 1}
  ],
  "schema_version": "2.0"
}
```

Les alias v1 (`id`, `serie`, `discipline`, `images`, `solution_ref`,
`concepts`, `span`, `concept`, `rationale`) sont acceptés à l'ingestion et
normalisés par `loweval.ingest_corpus` ; les fichiers **publiés** n'utilisent
que les noms v2.

## Chaîne de production

Voir `pipeline/readme.md` : scan (pdfsandwich) → OCR (Tesseract fra) →
nettoyage → segmentation v2 → consolidation JSONL → pré-annotation →
feuille CSV d'annotation.

## Qualité et limites connues

* Double annotation n = 150, seuil de convenance κ = 0,75 (Cohen) ;
  famille visuo-spatiale à κ = 0,74 : mention d'incertitude obligatoire.
* Les valeurs de `stem_concepts` et `bloom_level` issues de la
  pré-annotation automatique (étape 06) ne sont valables qu'après
  validation humaine.
* Toute modification du corpus incrémente `schema_version` et est tracée
  par `updated_at` en base (annexe C).

## Licence

CC BY-NC 4.0 — usage libre pour la recherche avec attribution ; les sujets
d'examen restent la propriété de l'État tchadien et sont publiés ici à des
fins de recherche uniquement.
