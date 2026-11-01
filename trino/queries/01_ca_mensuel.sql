-- ============================================================
--  KPI 1 : Chiffre d'affaires mensuel (avec croissance MoM)
-- ============================================================
-- Usage Trino : trino --server localhost:8085 -f 01_ca_mensuel.sql

SELECT
    annee,
    mois,
    mois_nom,
    trimestre,
    saison,
    ca_ht,
    LAG(ca_ht) OVER (ORDER BY annee, mois)          AS ca_mois_prec,
    ROUND(
        (ca_ht - LAG(ca_ht) OVER (ORDER BY annee, mois))
        / NULLIF(LAG(ca_ht) OVER (ORDER BY annee, mois), 0) * 100
    , 2)                                             AS croissance_mom_pct,
    -- Comparaison même mois année précédente (YoY)
    LAG(ca_ht, 12) OVER (ORDER BY annee, mois)      AS ca_meme_mois_n1,
    ROUND(
        (ca_ht - LAG(ca_ht, 12) OVER (ORDER BY annee, mois))
        / NULLIF(LAG(ca_ht, 12) OVER (ORDER BY annee, mois), 0) * 100
    , 2)                                             AS croissance_yoy_pct,
    -- Cumul annuel (YTD)
    SUM(ca_ht) OVER (PARTITION BY annee ORDER BY mois)  AS ca_ytd,
    marge_brute,
    taux_marge_pct,
    nb_transactions,
    panier_moyen
FROM (
    SELECT
        annee,
        mois,
        mois_nom,
        trimestre,
        saison,
        SUM(ca_ht)           AS ca_ht,
        SUM(marge_brute)     AS marge_brute,
        AVG(taux_marge_pct)  AS taux_marge_pct,
        SUM(nb_transactions) AS nb_transactions,
        AVG(panier_moyen)    AS panier_moyen
    FROM hive.ventes_dw.cube_mensuel_categorie
    GROUP BY annee, mois, mois_nom, trimestre, saison
)
ORDER BY annee, mois;
