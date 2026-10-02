# -*- coding: utf-8 -*-
"""Étape 6 — Pré-annotation automatique (concepts STEM et niveau de Bloom).

Propose des valeurs initiales pour `stem_concepts` et `bloom_level` à partir
de mots-clés présents dans l'énoncé. Correction majeure par rapport à
l'ancien script : les champs v1 (domain, subthemes, cognitive_level, tags)
n'existent plus dans le schéma 2.0 — seuls les champs du tableau 2.6 sont
écrits, et toujours à titre de PRÉ-ANNOTATION : la double annotation humaine
(κ ≥ 0,75, chapitre 2 §4) reste la source unique des étiquettes finales.

Ces valeurs automatiques servent uniquement d'aide à l'annotation : elles ne
doivent jamais figurer dans les résultats publiés sans validation humaine.

Usage : python pipeline/06_auto_enrich.py --input data/full/exercises_D.jsonl \
          --output data/full/exercises_D.enriched.jsonl
"""

import argparse
import json
import re
import unicodedata


def sans_accents(texte: str) -> str:
    """Retire les diacritiques (é -> e) pour matcher les mots-clés ASCII."""
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )

# Mots-clés indicatifs par concept STEM attendus au baccalauréat.
# Les correspondances restent volontairement grossières : l'annotateur
# tranche (voir guidelines/annotation_guide.md).
CONCEPTS_STEM = {
    "equation": ["équation", "resoudre", "racine"],
    "fonction": ["fonction", "derivee", "variation"],
    "limite": ["limite", "asymptote"],
    "geometrie": ["vecteur", "triangle", "cercle", "droite"],
    "probabilite": ["probabilite", "denombrement", "arbre"],
}

# Indices de niveau cognitif (taxonomie de Bloom, tableau 2.6) : la présence
# d'une consigne de démonstration fait basculer vers « analyser ». Les
# consignes sont stockées SANS accents : la comparaison se fait côté texte
# normalisé (sans_accents), faute de quoi « Demontrer » (OCR sans accent)
# ne matcherait jamais « démontrer ».
CONSIGNES_ANALYSER = ["demontrer", "montrez que", "prouver"]


def inferer_concepts(texte: str) -> list[str]:
    """Retourne les concepts STEM suggérés par les mots-clés de l'énoncé."""
    concepts = []
    texte_normalise = sans_accents(texte)
    for concept, mots_cles in CONCEPTS_STEM.items():
        if any(re.search(rf"\b{mot}\b", texte_normalise, re.IGNORECASE)
               for mot in mots_cles):
            concepts.append(concept)
    return concepts


def inferer_niveau_bloom(texte: str) -> str:
    """Propose un niveau de Bloom : « analyser » si démonstration requise,
    « appliquer » sinon (niveau dominant des sujets de bac observés)."""
    texte_normalise = sans_accents(texte)
    if any(re.search(consigne, texte_normalise, re.IGNORECASE)
           for consigne in CONSIGNES_ANALYSER):
        return "analyser"
    return "appliquer"


def main() -> None:
    """Point d'entrée CLI : enrichit un JSONL exercice par exercice."""
    analyseur = argparse.ArgumentParser(description="Pré-annotation concepts/Bloom (JSONL).")
    analyseur.add_argument("--input", required=True, help="JSONL d'entrée (étape 5)")
    analyseur.add_argument("--output", required=True, help="JSONL enrichi de sortie")
    arguments = analyseur.parse_args()

    compteur = 0
    with open(arguments.input, encoding="utf-8") as entree, \
            open(arguments.output, "w", encoding="utf-8") as sortie:
        for ligne in entree:
            ligne = ligne.strip()
            if not ligne:
                continue
            exercice = json.loads(ligne)

            # Renseignement uniquement si le champ est encore vide : une
            # valeur validée humainement n'est jamais écrasée.
            if not exercice.get("stem_concepts"):
                exercice["stem_concepts"] = inferer_concepts(exercice.get("statement", ""))
            if not exercice.get("bloom_level"):
                exercice["bloom_level"] = inferer_niveau_bloom(exercice.get("statement", ""))

            sortie.write(json.dumps(exercice, ensure_ascii=False) + "\n")
            compteur += 1

    print(f"Pré-annotation terminée : {compteur} exercice(s) -> {arguments.output}")
    print("Rappel : valeurs automatiques, à valider par la double annotation humaine.")


if __name__ == "__main__":
    main()
