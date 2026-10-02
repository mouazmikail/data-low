# Guide d'annotation — Data-Low (double annotation, n = 150)

## 1. Objectif

Produire des étiquettes d'erreurs **cohérentes** et **inter-opérables** sur
les productions d'élèves, source unique des analyses des chapitres 3 et 4.
L'accord inter-annotateur est mesuré par le κ de Cohen (seuil de
convenance : **0,75**, chapitre 2 §4) ; la famille visuo-spatiale, mesurée
à κ = 0,74, reste sous surveillance et ses analyses portent une mention
d'incertitude jusqu'au ré-arbitrage.

## 2. Avant de commencer

1. Lire l'énoncé **et** le corrigé de référence intégralement.
2. Vérifier la qualité OCR : tout doute sur un caractère se signale dans
   le champ `diagnostic` (« OCR douteux : … »), jamais en corrigeant
   silencieusement l'énoncé.
3. Ne jamais se fier à la pré-annotation automatique (étape 06 du
   pipeline) : c'est une aide de lecture, pas une étiquette.

## 3. Règles de saisie

* **Une erreur = une annotation.** Ne pas fusionner deux erreurs de
  natures différentes dans un seul enregistrement.
* `error_type` : choisir **une seule** famille parmi les cinq —
  `conceptuelle`, `procedurale`, `visuo-spatiale`, `linguistique`,
  `calculatoire` (définitions ci-dessous).
* `location` : citer le segment fautif **tel quel** (copier-coller depuis
  la copie), ou décrire la zone visuelle (« figure 2, triangle ABC »).
* `diagnostic` : justifier en une phrase pédagogique (« inversion de
  l'inégalité lors de la multiplication par un négatif »).
* `stem_concepts` : 1 à 3 concepts maximum, vocabulaire du programme.
* `bloom_level` : niveau **réellement exigé** par l'énoncé, pas le niveau
  supposé de l'élève.

## 4. Définitions des cinq familles (taxonomie 2.4)

| Famille | Définition | Exemple canonique |
|---|---|---|
| conceptuelle | incompréhension d'une notion ou d'une définition | confond dérivée et primitive |
| procedurale | étape de méthode omise ou mal ordonnée | oublie la discussion du discriminant |
| visuo-spatiale | erreur de lecture/usage d'une figure | rapporte la mesure au mauvais angle |
| linguistique | malentendu du texte de l'énoncé | intervertit « au moins » et « au plus » |
| calculatoire | faute de calcul pure | erreur de signe dans une factorisation |

## 5. Désaccords et arbitrage

1. Chaque exercice est annoté **deux fois** (expert_1, expert_2) à l'aveugle.
2. Les divergences sont listées par la requête
   `sql/cas_visuospatiaux_discordants.sql` et discutées en réunion
   d'arbitrage.
3. L'expert tiers tranche : l'étiquette retenue porte `arbitre = 1` ; c'est
   la seule prise en compte par les requêtes de l'annexe B et par le
   Low-Eval Kit.

## 6. Feuille de campagne

La feuille CSV est produite par `pipeline/07_export_csv.py`
(colonnes `annot_*`). Après saisie, les lignes sont reconverties en
enregistrements JSON v2 et validées par `loweval.ingest_corpus` avant
insertion dans la base annexe C (`scripts/ingest_data_low.py` du kit).
