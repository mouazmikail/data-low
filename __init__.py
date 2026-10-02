"""Data-Low — corpus annoté d'exercices du baccalauréat tchadien.

Ce package fournit les outils du pipeline de construction du corpus
(chapitre 2, figure 2.2) :

- ``ingest``      — collecte des sources hétérogènes (exports JSON/JSONL,
                    scans PDF/images) et conversion vers le schéma canonique ;
- ``ocr``         — OCR contrôlée à deux moteurs, pages douteuses marquées
                    ``a_relire`` avant tout usage ;
- ``segment``     — découpe des sujets en exercices, numérotation canonique
                    ``DISCIPLINE-ANNEE-SERIE-NNN`` ;
- ``validate``    — validation syntaxique des exercices, export JSONL ;
- ``annotate``    — complétude des annotations (solution de référence,
                    concepts) et contrôle des segments annotés ;
- ``qualite``     — double annotation (n = 150) et arbitrage des désaccords ;
- ``taxonomie``   — les cinq types d'erreur validés par l'étude pilote ;
- ``schema``      — miroir Python du schéma SQL, vérification croisée.

Le corpus source (sujets officiels 1975-2025, séries C et D) est distribué
séparément sous licence CC BY-NC 4.0 — voir MANIFEST.md.

Les sous-modules sont importés explicitement par les appelants (scripts,
tests) afin de garder l'import du paquet léger et sans effet de bord.
"""

__version__ = "2.0.0"

__all__ = ["__version__"]
