"""
Générateur de données synthétiques — Cube Analytique Ventes
============================================================
Produit ~500 000 transactions de vente sur 2 ans avec :
  - Saisonnalité (pics en décembre, été, soldes)
  - Tendance de croissance annuelle
  - Distribution réaliste des produits/clients/magasins
"""

import csv
import random
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Configuration encodage console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Reproductibilité ──────────────────────────────────────────
random.seed(42)

# ── Configuration ─────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent
START_DATE  = date(2023, 1, 1)
END_DATE    = date(2024, 12, 31)
N_VENTES    = 500_000   # nb de transactions
N_CLIENTS   = 10_000
N_PRODUITS  = 500
N_MAGASINS  = 50

# ── Référentiels ──────────────────────────────────────────────

CATEGORIES = {
    "Électronique":    ["Smartphone", "Tablette", "Laptop", "Casque audio", "Montre connectée"],
    "Vêtements":       ["T-shirt", "Pantalon", "Veste", "Robe", "Chaussures"],
    "Alimentation":    ["Café", "Chocolat", "Vin", "Fromage", "Confiture"],
    "Maison & Déco":   ["Lampe", "Coussin", "Cadre photo", "Vase", "Bougie"],
    "Sport & Loisirs": ["Vélo", "Tapis de yoga", "Haltères", "Sac de sport", "Gourde"],
}

SOUS_CATEGORIES = {
    "Smartphone": "Téléphonie", "Tablette": "Informatique", "Laptop": "Informatique",
    "Casque audio": "Audio", "Montre connectée": "Wearables",
    "T-shirt": "Hauts", "Pantalon": "Bas", "Veste": "Manteaux",
    "Robe": "Robes", "Chaussures": "Chaussures",
    "Café": "Boissons", "Chocolat": "Sucreries", "Vin": "Alcools",
    "Fromage": "Épicerie fine", "Confiture": "Épicerie fine",
    "Lampe": "Luminaires", "Coussin": "Textiles", "Cadre photo": "Décoration",
    "Vase": "Décoration", "Bougie": "Décoration",
    "Vélo": "Cyclisme", "Tapis de yoga": "Fitness", "Haltères": "Fitness",
    "Sac de sport": "Bagagerie", "Gourde": "Accessoires",
}

PRIX_BASE = {
    "Smartphone": 699, "Tablette": 449, "Laptop": 999, "Casque audio": 199,
    "Montre connectée": 299, "T-shirt": 25, "Pantalon": 55, "Veste": 120,
    "Robe": 75, "Chaussures": 90, "Café": 12, "Chocolat": 8, "Vin": 18,
    "Fromage": 15, "Confiture": 6, "Lampe": 45, "Coussin": 22, "Cadre photo": 18,
    "Vase": 35, "Bougie": 14, "Vélo": 450, "Tapis de yoga": 35,
    "Haltères": 60, "Sac de sport": 55, "Gourde": 25,
}

REGIONS = {
    "Île-de-France": ["Paris", "Versailles", "Boulogne-Billancourt"],
    "Auvergne-Rhône-Alpes": ["Lyon", "Grenoble", "Clermont-Ferrand"],
    "Provence-PACA": ["Marseille", "Nice", "Aix-en-Provence"],
    "Occitanie": ["Toulouse", "Montpellier", "Nîmes"],
    "Nouvelle-Aquitaine": ["Bordeaux", "Biarritz", "Limoges"],
    "Grand Est": ["Strasbourg", "Reims", "Nancy"],
    "Hauts-de-France": ["Lille", "Amiens", "Roubaix"],
    "Bretagne": ["Rennes", "Brest", "Nantes"],
}

SEGMENTS = ["Premium", "Standard", "Budget", "Entreprise", "Jeune"]
SEG_MULTIPLICATEURS = {"Premium": 1.6, "Standard": 1.0, "Budget": 0.75, "Entreprise": 1.2, "Jeune": 0.9}

TYPES_MAGASIN = ["Flagship", "Centre commercial", "Drive", "Centre-ville", "Outlet"]

# ── Utilitaires date ──────────────────────────────────────────

def date_vers_dict(d: date) -> dict:
    """Convertit une date en dict pour la dimension temps."""
    trimestres = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2,
                  7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 4}
    saisons = {12: "Hiver", 1: "Hiver", 2: "Hiver",
               3: "Printemps", 4: "Printemps", 5: "Printemps",
               6: "Été", 7: "Été", 8: "Été",
               9: "Automne", 10: "Automne", 11: "Automne"}
    return {
        "id_temps":    int(d.strftime("%Y%m%d")),
        "date":        d.isoformat(),
        "jour":        d.day,
        "mois":        d.month,
        "mois_nom":    d.strftime("%B"),
        "trimestre":   trimestres[d.month],
        "annee":       d.year,
        "semaine":     d.isocalendar()[1],
        "jour_semaine": d.strftime("%A"),
        "est_weekend":  int(d.weekday() >= 5),
        "saison":      saisons[d.month],
        "est_ferie":   int(d.month == 12 and d.day == 25 or
                          d.month == 1 and d.day == 1 or
                          d.month == 7 and d.day == 14 or
                          d.month == 5 and d.day == 1),
    }

def coefficient_saisonnalite(d: date) -> float:
    """Coefficient multiplicateur du volume de ventes selon la saisonnalité."""
    m = d.month
    # Pic décembre (fêtes), juillet-août (été), janvier (soldes)
    coefs = {1: 1.3, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.0, 6: 1.1,
             7: 1.2, 8: 1.1, 9: 0.95, 10: 1.0, 11: 1.15, 12: 1.8}
    # Weekend boost
    weekend_boost = 1.25 if d.weekday() >= 5 else 1.0
    return coefs[m] * weekend_boost

# ── Génération des dimensions ─────────────────────────────────

def gen_dim_temps():
    print("  → Génération dim_temps...")
    rows = []
    current = START_DATE
    while current <= END_DATE:
        rows.append(date_vers_dict(current))
        current += timedelta(days=1)
    return rows

def gen_dim_produit():
    print("  → Génération dim_produit...")
    rows = []
    pid = 1
    for cat, produits in CATEGORIES.items():
        for produit in produits:
            for variante in range(1, (N_PRODUITS // 25) + 1):
                marge = round(random.uniform(0.15, 0.55), 2)
                prix = round(PRIX_BASE[produit] * random.uniform(0.85, 1.25), 2)
                rows.append({
                    "id_produit":       pid,
                    "nom_produit":      f"{produit} v{variante}",
                    "categorie":        cat,
                    "sous_categorie":   SOUS_CATEGORIES[produit],
                    "marque":           f"Marque_{chr(65 + (pid % 10))}",
                    "prix_unitaire":    prix,
                    "cout_unitaire":    round(prix * (1 - marge), 2),
                    "taux_marge":       marge,
                    "actif":            1 if random.random() > 0.05 else 0,
                })
                pid += 1
                if pid > N_PRODUITS:
                    return rows
    return rows

def gen_dim_client():
    print("  → Génération dim_client...")
    rows = []
    regions = list(REGIONS.keys())
    for cid in range(1, N_CLIENTS + 1):
        region = random.choice(regions)
        segment = random.choices(SEGMENTS, weights=[10, 40, 25, 15, 10])[0]
        rows.append({
            "id_client":       cid,
            "nom_client":      f"Client_{cid:05d}",
            "segment":         segment,
            "region":          region,
            "ville":           random.choice(REGIONS[region]),
            "age":             random.randint(18, 75),
            "genre":           random.choice(["H", "F"]),
            "date_inscription": (START_DATE - timedelta(days=random.randint(0, 730))).isoformat(),
            "fidele":          int(random.random() > 0.6),
        })
    return rows

def gen_dim_magasin():
    print("  → Génération dim_magasin...")
    rows = []
    all_villes = [(v, r) for r, villes in REGIONS.items() for v in villes]
    for mid in range(1, N_MAGASINS + 1):
        ville, region = random.choice(all_villes)
        rows.append({
            "id_magasin":      mid,
            "nom_magasin":     f"Magasin_{mid:03d}_{ville[:3].upper()}",
            "type_magasin":    random.choice(TYPES_MAGASIN),
            "ville":           ville,
            "region":          region,
            "surface_m2":      random.choice([200, 500, 1000, 2000, 5000]),
            "nb_employes":     random.randint(5, 80),
            "ouvert":          1,
        })
    return rows

def gen_fact_ventes(clients, produits, magasins, dates_valides):
    print(f"  → Génération fact_ventes ({N_VENTES:,} transactions)...")
    rows = []
    all_dates = list(dates_valides.keys())
    total_jours = len(all_dates)

    for vid in range(1, N_VENTES + 1):
        if vid % 50_000 == 0:
            print(f"      {vid:,} / {N_VENTES:,}")

        # Choisir une date avec probabilité saisonnière
        d = random.choice(all_dates)
        coef = coefficient_saisonnalite(date.fromisoformat(dates_valides[d]["date"]))

        client   = random.choice(clients)
        produit  = random.choice(produits)
        magasin  = random.choice(magasins)

        # Quantité achetée (1–5, plus rare pour les produits chers)
        prix = produit["prix_unitaire"]
        max_qte = 5 if prix < 50 else (3 if prix < 200 else 2)
        qte = random.randint(1, max_qte)

        # Remise selon segment client
        seg_mult = SEG_MULTIPLICATEURS[client["segment"]]
        remise_pct = round(random.choices(
            [0, 0.05, 0.10, 0.15, 0.20, 0.30],
            weights=[40, 20, 15, 10, 10, 5]
        )[0], 2)

        prix_vente = round(prix * (1 - remise_pct), 2)
        montant_ht = round(prix_vente * qte, 2)
        tva = 0.20
        montant_ttc = round(montant_ht * (1 + tva), 2)
        cout = round(produit["cout_unitaire"] * qte, 2)
        marge = round(montant_ht - cout, 2)

        rows.append({
            "id_vente":       vid,
            "id_temps":       dates_valides[d]["id_temps"],
            "id_client":      client["id_client"],
            "id_produit":     produit["id_produit"],
            "id_magasin":     magasin["id_magasin"],
            "quantite":       qte,
            "prix_unitaire":  prix,
            "remise_pct":     remise_pct,
            "prix_vente":     prix_vente,
            "montant_ht":     montant_ht,
            "montant_ttc":    montant_ttc,
            "cout_total":     cout,
            "marge_brute":    marge,
            "canal_vente":    random.choices(
                ["En ligne", "Magasin", "Téléphone", "Application"],
                weights=[35, 50, 5, 10]
            )[0],
        })

    return rows

# ── Écriture CSV ──────────────────────────────────────────────

def write_csv(filename: str, rows: list):
    if not rows:
        return
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {filename} — {len(rows):,} lignes ({path.stat().st_size / 1024:.1f} KB)")

# ── Main ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Génération des données synthétiques")
    print("=" * 60)

    temps    = gen_dim_temps()
    produits = gen_dim_produit()
    clients  = gen_dim_client()
    magasins = gen_dim_magasin()

    # Index date → dict
    dates_index = {t["date"]: t for t in temps}

    ventes = gen_fact_ventes(clients, produits, magasins, dates_index)

    print("\nÉcriture des fichiers CSV...")
    write_csv("dim_temps.csv",    temps)
    write_csv("dim_produit.csv",  produits)
    write_csv("dim_client.csv",   clients)
    write_csv("dim_magasin.csv",  magasins)
    write_csv("fact_ventes.csv",  ventes)

    print("\n✅ Données générées avec succès !")
    print(f"   Dossier : {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
