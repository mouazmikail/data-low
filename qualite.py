"""Contrôle qualité : double annotation (n = 150) puis arbitrage (étape 5).

Le protocole du manuscrit impose, avant de figer le corpus :

1. **double annotation** d'un sous-échantillon de :data:`N_DOUBLE_ANNOTATION`
   exercices par deux annotateurs indépendants ;
2. **calcul du κ de Cohen par type** d'erreur (fonction
   :func:`data_low.taxonomie.kappa_par_type`) ;
3. **arbitrage** de chaque paire en désaccord par un troisième annotateur
   (arbitre), dont la décision devient l'étiquette de référence.

Le point d'entrée :func:`conduire_double_annotation` simule / rejoue ce
protocole sur un lot de paires de verdicts et produit le rapport attendu
par la section 2.4 (kappas, types à renforcer, taux d'accord brut).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data_low.taxonomie import (
    KAPPA_PILOTE,
    TYPES_ERREUR,
    kappa_par_type,
    types_a_renforcer,
)

#: Taille du sous-échantillon doublement annoté (section 2.4 du manuscrit).
N_DOUBLE_ANNOTATION = 150


@dataclass
class RapportQualite:
    """Bilan du contrôle qualité d'un corpus annoté.

    Attributes:
        nb_paires: nombre de paires de verdicts analysées.
        accord_brut: proportion de paires d'accord (avant arbitrage).
        kappas: κ de Cohen par type d'erreur.
        types_a_renforcer: types sous le seuil de 0.75 (guide renforcé).
        kappas_pilote: kappas de référence du tableau 2.4 (comparaison).
    """

    nb_paires: int = 0
    accord_brut: float = 0.0
    kappas: dict[str, float] = field(default_factory=dict)
    types_a_renforcer: list[str] = field(default_factory=list)
    kappas_pilote: dict[str, float] = field(default_factory=lambda: dict(KAPPA_PILOTE))

    def conforme(self) -> bool:
        """Vrai si aucun type n'est sous le seuil de fiabilité (0.75)."""
        return not self.types_a_renforcer


def conduire_double_annotation(
    paires: list[dict[str, Any]],
) -> RapportQualite:
    """Rejoue le protocole de double annotation sur un lot de paires de verdicts.

    Chaque paire est un dictionnaire ``{type_a, type_b, error_type}`` où
    ``type_a``/``type_b`` sont les verdicts des deux annotateurs sur la
    cible ``error_type``. Le rapport combine :
      * le taux d'accord brut (part des paires identiques) ;
      * le κ par type (:func:`data_low.taxonomie.kappa_par_type`) ;
      * la liste des types sous le seuil, à renforcer avant arbitrage.

    :raises ValueError: si le lot dépasse la taille du sous-échantillon
        prévu (signal de fuite du protocole — la double annotation ne doit
        porter que sur les 150 exercices dédiés).
    """
    if len(paires) > N_DOUBLE_ANNOTATION:
        raise ValueError(
            f"Le lot compte {len(paires)} paires, au-delà des "
            f"{N_DOUBLE_ANNOTATION} prévues par le protocole."
        )

    rapport = RapportQualite(nb_paires=len(paires))
    if not paires:
        return rapport

    # 1. Accord brut : part des paires où les deux annotateurs sont d'accord.
    accords = sum(1 for p in paires if p["type_a"] == p["type_b"])
    rapport.accord_brut = round(accords / len(paires), 3)

    # 2. κ par type + alerte sur les types sous le seuil.
    rapport.kappas = kappa_par_type(paires)
    rapport.types_a_renforcer = types_a_renforcer(rapport.kappas)
    return rapport


def arbitrer(paire: dict[str, Any], decision: str, arbitre: str,
             justification: str = "") -> dict[str, Any]:
    """Formalise la décision d'arbitrage d'une paire en désaccord.

    Retourne un enregistrement prêt pour la table ``arbitrages`` du schéma
    SQLite ; la décision devient l'étiquette de référence du corpus.
    """
    if decision not in TYPES_ERREUR:
        raise ValueError(f"Décision d'arbitrage hors taxonomie : {decision!r}")
    if paire.get("type_a") == paire.get("type_b"):
        raise ValueError("Arbitrage inutile : la paire est déjà d'accord.")
    return {
        "exercise_id": paire.get("exercise_id", ""),
        "arbitre": arbitre,
        "decision": decision,
        "justification": justification,
        "accord_initial": False,
    }
