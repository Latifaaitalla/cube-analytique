-- ============================================================
--  KPI 4 : Analyse par segment client (RFM simplifié)
-- ============================================================
-- RFM = Récence, Fréquence, Montant (valeur client)

WITH client_stats AS (
    SELECT
        c.id_client,
        c.segment,
        c.region,
        c.age,
        c.genre,
        c.fidele,
        COUNT(DISTINCT f.id_vente)   AS nb_achats,
        ROUND(SUM(f.montant_ht), 2)  AS ca_total_client,
        ROUND(AVG(f.montant_ht), 2)  AS panier_moyen,
        ROUND(SUM(f.marge_brute), 2) AS marge_generee,
        MAX(t.annee * 100 + t.mois)  AS derniere_periode
    FROM hive.ventes_dw.fact_ventes f
    JOIN hive.ventes_dw.dim_client c ON f.id_client = c.id_client
    JOIN hive.ventes_dw.dim_temps  t ON f.id_temps  = t.id_temps
    GROUP BY c.id_client, c.segment, c.region, c.age, c.genre, c.fidele
),
segment_stats AS (
    SELECT
        segment,
        COUNT(*)                          AS nb_clients,
        ROUND(AVG(nb_achats), 1)          AS freq_achat_moy,
        ROUND(AVG(ca_total_client), 2)    AS ltv_moyenne,       -- Life Time Value
        ROUND(SUM(ca_total_client), 0)    AS ca_total_segment,
        ROUND(AVG(panier_moyen), 2)       AS panier_moyen,
        ROUND(AVG(marge_generee), 2)      AS marge_par_client,
        ROUND(SUM(marge_generee), 0)      AS marge_totale_segment,
        ROUND(
            SUM(ca_total_client) / SUM(SUM(ca_total_client)) OVER () * 100
        , 2)                              AS part_ca_pct
    FROM client_stats
    GROUP BY segment
)
SELECT
    segment,
    nb_clients,
    freq_achat_moy,
    ltv_moyenne,
    ca_total_segment,
    panier_moyen,
    marge_par_client,
    marge_totale_segment,
    part_ca_pct,
    RANK() OVER (ORDER BY ltv_moyenne DESC) AS rang_ltv
FROM segment_stats
ORDER BY ca_total_segment DESC;
