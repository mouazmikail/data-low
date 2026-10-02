-- =============================================================================
-- cas_visuospatiaux_discordants.sql — v1.0 (annexe B du manuscrit)
-- Items à soumettre au troisième annotateur (ré-arbitrage cible) :
-- étiquettes divergentes sur la famille visuo-spatiale.
--
-- Tant que ces items ne sont pas ré-arbitragés, les analyses de la famille
-- visuo-spatiale (tableau 4.7) portent une mention d'incertitude.
-- =============================================================================
SELECT
    a.exercise_id
FROM
    annotations a
JOIN
    erreurs e ON e.id_erreur = a.id_erreur
WHERE
    a.campagne = 'double_annotation_2026'
    AND e.type_erreur = 'visuo-spatiale'
GROUP BY
    a.exercise_id
HAVING
    COUNT(DISTINCT a.id_erreur) > 1
    OR COUNT(DISTINCT a.annotator) > 1
       AND COUNT(*) > 1;
