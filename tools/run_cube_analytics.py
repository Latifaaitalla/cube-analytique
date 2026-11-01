"""
Exécution locale du Cube Analytique (SQLite in-memory)
Permet de visualiser immédiatement les résultats des 5 requêtes Trino
sans nécessiter le démarrage du cluster Docker lourd.
"""

import sqlite3
import csv
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

def load_data(conn):
    cur = conn.cursor()
    print("⏳ Chargement des 500 000 transactions en mémoire...")
    t0 = time.time()

    # Dim Temps
    cur.execute("""
    CREATE TABLE dim_temps (
        id_temps INT PRIMARY KEY, date TEXT, jour INT, mois INT, mois_nom TEXT,
        trimestre INT, annee INT, semaine INT, jour_semaine TEXT,
        est_weekend INT, saison TEXT, est_ferie INT
    )""")
    with open(DATA_DIR / "dim_temps.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        cur.executemany("INSERT INTO dim_temps VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", r)

    # Dim Produit
    cur.execute("""
    CREATE TABLE dim_produit (
        id_produit INT PRIMARY KEY, nom_produit TEXT, categorie TEXT, sous_categorie TEXT,
        marque TEXT, prix_unitaire REAL, cout_unitaire REAL, taux_marge REAL, actif INT
    )""")
    with open(DATA_DIR / "dim_produit.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        cur.executemany("INSERT INTO dim_produit VALUES (?,?,?,?,?,?,?,?,?)", r)

    # Dim Client
    cur.execute("""
    CREATE TABLE dim_client (
        id_client INT PRIMARY KEY, nom_client TEXT, segment TEXT, region TEXT, ville TEXT,
        age INT, genre TEXT, date_inscription TEXT, fidele INT
    )""")
    with open(DATA_DIR / "dim_client.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        cur.executemany("INSERT INTO dim_client VALUES (?,?,?,?,?,?,?,?,?)", r)

    # Dim Magasin
    cur.execute("""
    CREATE TABLE dim_magasin (
        id_magasin INT PRIMARY KEY, nom_magasin TEXT, type_magasin TEXT, ville TEXT, region TEXT,
        surface_m2 INT, nb_employes INT, ouvert INT
    )""")
    with open(DATA_DIR / "dim_magasin.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        cur.executemany("INSERT INTO dim_magasin VALUES (?,?,?,?,?,?,?,?)", r)

    # Fact Ventes
    cur.execute("""
    CREATE TABLE fact_ventes (
        id_vente INT PRIMARY KEY, id_temps INT, id_client INT, id_produit INT, id_magasin INT,
        quantite INT, prix_unitaire REAL, remise_pct REAL, prix_vente REAL,
        montant_ht REAL, montant_ttc REAL, cout_total REAL, marge_brute REAL, canal_vente TEXT
    )""")
    with open(DATA_DIR / "fact_ventes.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        cur.executemany("INSERT INTO fact_ventes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r)

    conn.commit()
    print(f"✓ Données chargées avec succès en {time.time() - t0:.2f}s !\n")

def print_separator(title):
    print("=" * 80)
    print(f"  📊 {title}")
    print("=" * 80)

def run_analytics(conn):
    cur = conn.cursor()

    # 1. Synthèse Globale
    print_separator("SYNTHÈSE GLOBALE (2023 - 2024)")
    cur.execute("""
    SELECT 
        t.annee, 
        COUNT(*) as nb_transactions, 
        COUNT(DISTINCT f.id_client) as nb_clients,
        ROUND(SUM(f.montant_ht), 2) as ca_ht,
        ROUND(AVG(f.montant_ht), 2) as panier_moyen,
        ROUND(SUM(f.marge_brute), 2) as marge_brute,
        ROUND(SUM(f.marge_brute)/SUM(f.montant_ht)*100, 2) as taux_marge_pct
    FROM fact_ventes f
    JOIN dim_temps t ON f.id_temps = t.id_temps
    GROUP BY t.annee
    ORDER BY t.annee
    """)
    rows = cur.fetchall()
    print(f"{'Année':<8} | {'Transactions':<14} | {'Clients':<10} | {'CA Total HT (€)':<18} | {'Panier (€)':<10} | {'Marge (€)':<16} | {'Taux Marge'}")
    print("-" * 88)
    for r in rows:
        print(f"{r[0]:<8} | {r[1]:<14,d} | {r[2]:<10,d} | {r[3]:<18,.2f} | {r[4]:<10.2f} | {r[5]:<16,.2f} | {r[6]}%")

    # 2. Top 10 Produits
    print("\n")
    print_separator("TOP 10 PRODUITS PAR CHIFFRE D'AFFAIRES (2024)")
    cur.execute("""
    SELECT 
        p.nom_produit,
        p.categorie,
        SUM(f.quantite) as volume,
        ROUND(SUM(f.montant_ht), 2) as ca_ht,
        ROUND(SUM(f.marge_brute), 2) as marge_brute,
        ROUND(SUM(f.marge_brute)/SUM(f.montant_ht)*100, 2) as taux_marge
    FROM fact_ventes f
    JOIN dim_produit p ON f.id_produit = p.id_produit
    JOIN dim_temps t ON f.id_temps = t.id_temps
    WHERE t.annee = 2024
    GROUP BY p.id_produit, p.nom_produit, p.categorie
    ORDER BY ca_ht DESC
    LIMIT 10
    """)
    rows = cur.fetchall()
    print(f"{'Rang':<5} | {'Produit':<22} | {'Catégorie':<16} | {'Volume':<8} | {'CA HT (€)':<15} | {'Marge (€)':<14} | {'Taux'}")
    print("-" * 92)
    for i, r in enumerate(rows, 1):
        print(f"{i:<5} | {r[0]:<22} | {r[1]:<16} | {r[2]:<8,d} | {r[3]:<15,.2f} | {r[4]:<14,.2f} | {r[5]}%")

    # 3. Performance Régionale
    print("\n")
    print_separator("PERFORMANCE PAR RÉGION (2024)")
    cur.execute("""
    WITH reg_ca AS (
        SELECT 
            m.region,
            COUNT(DISTINCT f.id_vente) as nb_transactions,
            ROUND(SUM(f.montant_ht), 2) as ca_ht,
            ROUND(AVG(f.montant_ht), 2) as panier_moyen,
            ROUND(SUM(f.marge_brute), 2) as marge_brute
        FROM fact_ventes f
        JOIN dim_magasin m ON f.id_magasin = m.id_magasin
        JOIN dim_temps t ON f.id_temps = t.id_temps
        WHERE t.annee = 2024
        GROUP BY m.region
    )
    SELECT 
        region,
        nb_transactions,
        ca_ht,
        panier_moyen,
        marge_brute,
        ROUND(ca_ht / (SELECT SUM(ca_ht) FROM reg_ca) * 100, 2) as part_pct
    FROM reg_ca
    ORDER BY ca_ht DESC
    """)
    rows = cur.fetchall()
    print(f"{'Région':<24} | {'Transactions':<14} | {'CA HT (€)':<16} | {'Panier (€)':<10} | {'Marge (€)':<14} | {'Part %'}")
    print("-" * 92)
    for r in rows:
        print(f"{r[0]:<24} | {r[1]:<14,d} | {r[2]:<16,.2f} | {r[3]:<10.2f} | {r[4]:<14,.2f} | {r[5]}%")

    # 4. Segments Clients
    print("\n")
    print_separator("ANALYSE PAR SEGMENT CLIENT")
    cur.execute("""
    WITH client_kpis AS (
        SELECT 
            c.id_client,
            c.segment,
            COUNT(DISTINCT f.id_vente) as nb_achats,
            SUM(f.montant_ht) as ca_client,
            SUM(f.marge_brute) as marge_client
        FROM fact_ventes f
        JOIN dim_client c ON f.id_client = c.id_client
        GROUP BY c.id_client, c.segment
    )
    SELECT 
        segment,
        COUNT(*) as nb_clients,
        ROUND(AVG(nb_achats), 1) as freq_achat_moy,
        ROUND(AVG(ca_client), 2) as ltv_moyenne,
        ROUND(SUM(ca_client), 2) as ca_total_segment,
        ROUND(AVG(ca_client / nb_achats), 2) as panier_moyen,
        ROUND(SUM(ca_client) / (SELECT SUM(montant_ht) FROM fact_ventes) * 100, 2) as part_ca_pct
    FROM client_kpis
    GROUP BY segment
    ORDER BY ca_total_segment DESC
    """)
    rows = cur.fetchall()
    print(f"{'Segment':<14} | {'Clients':<10} | {'Nb Achats':<10} | {'LTV Moyenne (€)':<16} | {'CA Total (€)':<16} | {'Panier (€)':<10} | {'Part %'}")
    print("-" * 92)
    for r in rows:
        print(f"{r[0]:<14} | {r[1]:<10,d} | {r[2]:<10.1f} | {r[3]:<16,.2f} | {r[4]:<16,.2f} | {r[5]:<10.2f} | {r[6]}%")

    # 5. Canaux de Vente
    print("\n")
    print_separator("RÉPARTITION PAR CANAL DE VENTE (2024)")
    cur.execute("""
    SELECT 
        f.canal_vente,
        COUNT(*) as nb_transactions,
        ROUND(SUM(f.montant_ht), 2) as ca_ht,
        ROUND(AVG(f.montant_ht), 2) as panier_moyen,
        ROUND(SUM(f.montant_ht) / (SELECT SUM(montant_ht) FROM fact_ventes JOIN dim_temps t ON fact_ventes.id_temps = t.id_temps WHERE t.annee = 2024) * 100, 2) as part_ca_pct
    FROM fact_ventes f
    JOIN dim_temps t ON f.id_temps = t.id_temps
    WHERE t.annee = 2024
    GROUP BY f.canal_vente
    ORDER BY ca_ht DESC
    """)
    rows = cur.fetchall()
    print(f"{'Canal':<16} | {'Transactions':<14} | {'CA HT (€)':<16} | {'Panier (€)':<10} | {'Part %'}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:<16} | {r[1]:<14,d} | {r[2]:<16,.2f} | {r[3]:<10.2f} | {r[4]}%")

def main():
    conn = sqlite3.connect(":memory:")
    load_data(conn)
    run_analytics(conn)
    conn.close()

if __name__ == "__main__":
    main()

