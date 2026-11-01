-- ============================================================
--  KPI 2 : Top 10 produits par CA et par catégorie (annuel)
-- ============================================================

WITH produits_rang AS (
    SELECT
        annee,
        id_produit,
        nom_produit,
        categorie,
        sous_categorie,
        marque,
        ca_ht,
        volume_ventes,
        marge_brute,
        taux_marge_pct,
        nb_transactions,
        rang_ca,
        -- Part de marché dans la catégorie
        ROUND(
            ca_ht / SUM(ca_ht) OVER (PARTITION BY annee, categorie) * 100
        , 2) AS part_marche_categorie_pct
    FROM hive.ventes_dw.cube_produit_top
)
SELECT
    annee,
    rang_ca,
    nom_produit,
    categorie,
    sous_categorie,
    marque,
    ROUND(ca_ht, 0)             AS ca_ht,
    volume_ventes,
    ROUND(marge_brute, 0)       AS marge_brute,
    taux_marge_pct,
    nb_transactions,
    part_marche_categorie_pct
FROM produits_rang
WHERE rang_ca <= 10
ORDER BY annee DESC, rang_ca ASC;
