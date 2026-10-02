"""Taxonomie des erreurs et agrégation de la double annotation.

La taxonomie à cinq types provient de l'étude pilote (tableau 2.4 du
manuscrit) : conceptuelle, procédurale, visuo-spatiale, linguistique et
calculatoire. Les coefficients kappa de Cohen observés par type sont :

==============  =====
Type d'erreur   κ
==============  =====
conceptuelle    0.88
procedurale     0.81
visuo-spatiale  0.79
linguistique    0.76
calculatoire    0.74   ← sous le seuil de 0.75 (signal d'alerte)
==============  =====

Le seuil de fiabilité conventionnel (Landis & Koch) est ici fixé à
**0.75** : un type dont le κ tombe sous cette valeur doit faire l'objet
d'un guide d'annotation renforcé et d'une nouvelle passe d'arbitrage.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

# ---------------------------------------------------------------------------
# 1. Constantes de la taxonomie
# ---------------------------------------------------------------------------
#: Ordre canonique des cinq types (utilisé pour les rapports et la matrice
#: de confusion) — ne pas réordonner sans mettre à jour le schéma SQL.
TYPES_ERREUR: tuple[str, ...] = (
    "conceptuelle",
    "procedurale",
    "visuo-spatiale",
    "linguistique",
    "calculatoire",
)

#: Libellés longs, utilisés dans les fiches de rapport et la documentation.
LIBELLES_TYPES: dict[str, str] = {
    "conceptuelle": "Erreur conceptuelle (incompréhension d'une notion)",
    "procedurale": "Erreur procédurale (étape de raisonnement fautive)",
    "visuo-spatiale": "Erreur visuo-spatiale (lecture ou interprétation d'une figure)",
    "linguistique": "Erreur linguistique (compréhension de la consigne)",
    "calculatoire": "Erreur calculatoire (faute opératoire ou arithmétique)",
}

#: Seuil de fiabilité par type (kappa de Cohen). Sous ce seuil, le type
#: est marqué « à renforcer » dans le rapport de contrôle qualité.
SEUIL_KAPPA = 0.75

#: Kappas de référence observés lors de l'étude pilote (tableau 2.4).
#: Sert de valeur attendue au test de non-régression ``test_kappa_pilote``.
KAPPA_PILOTE: dict[str, float] = {
    "conceptuelle": 0.88,
    "procedurale": 0.81,
    "visuo-spatiale": 0.79,
    "linguistique": 0.76,
    "calculatoire": 0.74,
}

# ---------------------------------------------------------------------------
# 2. Kappa de Cohen sur les double annotations
# ---------------------------------------------------------------------------


def kappa_par_type(
    double_annotations: Iterable[dict[str, object]],
) -> dict[str, float]:
    """Calcule le κ de Cohen par type d'erreur à partir des double annotations.

    Chaque dictionnaire d'entrée doit contenir au moins les clés
    ``type_a`` et ``type_b`` (verdicts des deux annotateurs) et éventuellement
    ``error_type`` pour ne retenir que les paires portant sur le même type
    cible. La fonction retourne un κ par type présent dans les données ;
    un type sans paire retournable n'apparaît pas dans le résultat.

    :param double_annotations: itérable de verdicts ``{type_a, type_b, ...}``.
    :return: ``{type: kappa}`` arrondi à deux décimales.
    """
    from Low-Eval-Kit.metrics import cohen_kappa  # import local : évite cycle

    # 1. Regroupement des verdicts par type cible (clé ``error_type`` quand
    #    elle est disponible, sinon on compare directement type_a/type_b).
    veridicts: dict[str, list[tuple[str, str]]] = {}
    for paire in double_annotations:
        ta, tb = str(paire["type_a"]), str(paire["type_b"])
        cible = str(paire.get("error_type", ta))
        veridicts.setdefault(cible, []).append((ta, tb))

    # 2. Calcul du κ par type sur les deux colonnes de verdicts.
    #    Cas dégénéré : un seul type observé partout → accord parfait (κ = 1.0).
    kappas: dict[str, float] = {}
    for cible, paires in veridicts.items():
        a = [p[0] for p in paires]
        b = [p[1] for p in paires]
        if len(set(a) | set(b)) == 1:
            kappas[cible] = 1.0
            continue
        kappas[cible] = round(cohen_kappa(a, b), 2)
    return kappas


def types_a_renforcer(kappas: dict[str, float]) -> list[str]:
    """Retourne les types dont le κ est sous le seuil de fiabilité.

    C'est exactement le signal d'alerte que le manuscrit relève pour le
    type « calculatoire » (κ = 0.74 < 0.75) : il justifie un guide
    d'annotation renforcé avant la phase d'arbitrage.
    """
    # Seuls les types réellement observés (présents dans ``kappas``) sont
    # jugés : un type absent du lot ne peut pas être « sous le seuil »
    # (sinon tout lot partiel serait entièrement « à renforcer »).
    return [t for t, k in kappas.items() if k < SEUIL_KAPPA]


def distribution_annotations(
    annotations: Iterable[dict[str, object]],
) -> Counter:
    """Compte les annotations par type (pour la fiche descriptive du corpus)."""
    return Counter(str(a["error_type"]) for a in annotations)
