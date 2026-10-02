-- =============================================================================
-- parts_taxonomie_erreurs.sql — v1.0 (annexe B du manuscrit)
-- Parts des cinq familles d'erreurs dans l'échantillon annoté de Data-Low
-- (campagne figée : double annotation, n = 150).
--
-- Résultat attendu (tableau 2.4 / figure 2.4) : calculatoire en tête,
-- visuo-spatiale dernière — la famille sous surveillance (κ = 0,74).
-- =============================================================================
SELECT
    e.type_erreur,
    COUNT(*)                                          AS n_cas,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS part_pct
FROM
    annotations a
JOIN
    erreurs e ON e.id_erreur = a.id_erreur
WHERE
    a.campagne = 'double_annotation_2026'
    AND a.arbitre = 1            -- étiquette finale après arbitrage
GROUP BY
    e.type_erreur
ORDER BY
    n_cas DESC;
