-- ============================================================
--  KPI 5 : Analyse canal de vente + saisonnalité
-- ============================================================

-- 5a. CA par canal et par trimestre
SELECT
    annee,
    trimestre      AS trim,
    mois,
    canal_vente,
    nb_transactions,
    ROUND(ca_ht, 0)          AS ca_ht,
    ROUND(panier_moyen, 2)   AS panier_moyen,
    ROUND(marge_brute, 0)    AS marge_brute,
    -- Part canal dans le mois
    ROUND(
        ca_ht / SUM(ca_ht) OVER (PARTITION BY annee, mois) * 100
    , 2)                     AS part_canal_pct
FROM hive.ventes_dw.cube_mensuel_canal
JOIN (
    SELECT DISTINCT annee, mois, trimestre
    FROM hive.ventes_dw.cube_mensuel_categorie
) t USING (annee, mois)
ORDER BY annee, mois, ca_ht DESC;
