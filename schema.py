"""Miroir Python du schéma SQL ``data_low/schema.sql`` (annexe B).

Le schéma SQL est la **source unique** de vérité structurelle (tables,
contraintes ``CHECK``, colonnes). Ce module en expose les valeurs contrôlées
en constantes Python pour deux usages :

* référencement direct dans le code (p. ex. lister les tables attendues
  sans ouvrir la base) ;
* :func:`verifier_coherence_avec_sql` — garde-fou d'intégrité : les cinq
  types de la taxonomie Python (``data_low.taxonomie.TYPES_ERREUR``) et les
  trois environnements (``loweval.config.ENVIRONNEMENTS_VALIDES``) doivent
  correspondre **exactement** aux listes inscrites dans le ``CHECK`` du
  schéma SQL. Toute divergence est un bug de construction du dépôt.

Historique (version 2.0) : ajout de ``runs.metadonnees`` (JSON, huit
métadonnées §7.2), de ``runs.vram_gb`` (pic VRAM réel, en remplacement du
``0.0`` factice de l'ancien protocole terrain) et des tables de double
annotation / arbitrage (contrôle qualité, §2.4).
"""

from __future__ import annotations

import re
from pathlib import Path

#: Tables du schéma (ordre = ordre de création dans le fichier SQL).
TABLES = (
    "exercises",
    "annotations",
    "double_annotations",
    "arbitrages",
    "runs",
    "results",
)

#: Colonnes de la table ``runs`` ajoutées en version 2.0 (correctifs).
COLONNES_RUNS_V2 = ("metadonnees", "vram_gb")

#: Environnements contrôlés par le ``CHECK`` de ``runs.environment``.
ENVIRONNEMENTS_SQL = ("cloud", "local", "terrain")

#: Les cinq types d'erreur de la taxonomie, repris dans les contraintes
#: ``CHECK`` des tables ``annotations``, ``double_annotations`` et
#: ``arbitrages``. Source unique : ``data_low.taxonomie.TYPES_ERREUR`` ;
#: cette constante n'existe que pour la vérification croisée.
TYPES_ERREUR_SQL = (
    "conceptuelle", "procedurale", "visuo-spatiale",
    "linguistique", "calculatoire",
)

#: Chemin du fichier SQL canonique, relatif à ce module.
CHEMIN_SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"


def lire_schema_sql() -> str:
    """Retourne le contenu textuel du schéma SQL canonique."""
    return CHEMIN_SCHEMA_SQL.read_text(encoding="utf-8")


def verifier_coherence_avec_sql() -> list[str]:
    """Compare les constantes Python aux contraintes du schéma SQL.

    Retourne la liste des divergences trouvées (vide = tout est cohérent).
    Appelé par les tests et par ``scripts/build_data_low.py`` avant toute
    insertion : un ``CHECK`` SQL désynchronisé de la taxonomie Python
    laisserait passer (ou rejeterait à tort) des annotations.
    """
    problemes: list[str] = []

    sql = lire_schema_sql()

    # -- 1. Les cinq types apparaissent dans au moins un CHECK --------------
    for type_erreur in TYPES_ERREUR_SQL:
        if f"'{type_erreur}'" not in sql:
            problemes.append(
                f"type « {type_erreur} » absent du schéma SQL {CHEMIN_SCHEMA_SQL.name}."
            )

    # -- 2. Alignement avec la taxonomie Python -----------------------------
    from data_low.taxonomie import TYPES_ERREUR
    if tuple(TYPES_ERREUR) != TYPES_ERREUR_SQL:
        problemes.append(
            "data_low.taxonomie.TYPES_ERREUR et data_low.schema."
            "TYPES_ERREUR_SQL divergent : " f"{TYPES_ERREUR} ≠ {TYPES_ERREUR_SQL}."
        )

    # -- 3. Alignement avec les environnements de loweval.config ------------
    from Low-Eval-Kit.config import ENVIRONNEMENTS_VALIDES
    if tuple(ENVIRONNEMENTS_VALIDES) != ENVIRONNEMENTS_SQL:
        problemes.append(
            "loweval.config.ENVIRONNEMENTS_VALIDES et data_low.schema."
            "ENVIRONNEMENTS_SQL divergent : "
            f"{ENVIRONNEMENTS_VALIDES} ≠ {ENVIRONNEMENTS_SQL}."
        )

    # -- 4. Les colonnes v2.0 existent bien dans le fichier SQL -------------
    for colonne in COLONNES_RUNS_V2:
        if not re.search(rf"^\s*{colonne}\s+", sql, flags=re.MULTILINE):
            problemes.append(
                f"colonne « {colonne} » (v2.0) absente de {CHEMIN_SCHEMA_SQL.name}."
            )
    return problemes
