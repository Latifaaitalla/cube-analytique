-- ============================================================
--  KPI 3 : Performance par région et type de magasin
-- ============================================================

SELECT
    annee,
    region,
    type_magasin,
    SUM(nb_transactions)                              AS nb_transactions,
    SUM(nb_clients_actifs)                            AS nb_clients_actifs,
    ROUND(SUM(ca_ht), 0)                              AS ca_ht,
    ROUND(AVG(panier_moyen), 2)                       AS panier_moyen,
    ROUND(SUM(marge_brute), 0)                        AS marge_brute,
    -- Part du CA national
    ROUND(
        SUM(ca_ht) / SUM(SUM(ca_ht)) OVER (PARTITION BY annee) * 100
    , 2)                                              AS part_ca_national_pct,
    -- Rang régional
    RANK() OVER (PARTITION BY annee ORDER BY SUM(ca_ht) DESC) AS rang_region,
    -- CA par client
    ROUND(SUM(ca_ht) / NULLIF(SUM(nb_clients_actifs), 0), 2) AS ca_par_client
FROM hive.ventes_dw.cube_mensuel_region
GROUP BY annee, region, type_magasin
ORDER BY annee DESC, ca_ht DESC;
