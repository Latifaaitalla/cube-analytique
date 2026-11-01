"""
Pipeline ETL Spark SQL — Cube Analytique Ventes
================================================
Étapes :
  1. Lecture des CSV bruts (depuis MinIO / local)
  2. Nettoyage & validation des données
  3. Construction du schéma en étoile (Parquet partitionné)
  4. Enregistrement dans le Hive Metastore
  5. Création du cube OLAP (tables agrégées pré-calculées)
  6. Calcul des KPIs de synthèse

Usage (depuis Spark master) :
  spark-submit --master spark://spark-master:7077 \
               /opt/spark-jobs/etl_pipeline.py
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, IntegerType, StringType,
    DoubleType, DateType
)

# ─────────────────────────────────────────────────────────────
# 1. Initialisation de la session Spark
# ─────────────────────────────────────────────────────────────

def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CubeAnalytique-ETL")
        .config("spark.sql.catalogImplementation", "hive")
        .config("spark.sql.warehouse.dir", "/opt/warehouse")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .enableHiveSupport()
        .getOrCreate()
    )

# ─────────────────────────────────────────────────────────────
# 2. Schémas des données brutes
# ─────────────────────────────────────────────────────────────

SCHEMA_TEMPS = StructType([
    StructField("id_temps",     IntegerType()),
    StructField("date",         StringType()),
    StructField("jour",         IntegerType()),
    StructField("mois",         IntegerType()),
    StructField("mois_nom",     StringType()),
    StructField("trimestre",    IntegerType()),
    StructField("annee",        IntegerType()),
    StructField("semaine",      IntegerType()),
    StructField("jour_semaine", StringType()),
    StructField("est_weekend",  IntegerType()),
    StructField("saison",       StringType()),
    StructField("est_ferie",    IntegerType()),
])

SCHEMA_PRODUIT = StructType([
    StructField("id_produit",      IntegerType()),
    StructField("nom_produit",     StringType()),
    StructField("categorie",       StringType()),
    StructField("sous_categorie",  StringType()),
    StructField("marque",          StringType()),
    StructField("prix_unitaire",   DoubleType()),
    StructField("cout_unitaire",   DoubleType()),
    StructField("taux_marge",      DoubleType()),
    StructField("actif",           IntegerType()),
])

SCHEMA_CLIENT = StructType([
    StructField("id_client",        IntegerType()),
    StructField("nom_client",       StringType()),
    StructField("segment",          StringType()),
    StructField("region",           StringType()),
    StructField("ville",            StringType()),
    StructField("age",              IntegerType()),
    StructField("genre",            StringType()),
    StructField("date_inscription", StringType()),
    StructField("fidele",           IntegerType()),
])

SCHEMA_MAGASIN = StructType([
    StructField("id_magasin",   IntegerType()),
    StructField("nom_magasin",  StringType()),
    StructField("type_magasin", StringType()),
    StructField("ville",        StringType()),
    StructField("region",       StringType()),
    StructField("surface_m2",   IntegerType()),
    StructField("nb_employes",  IntegerType()),
    StructField("ouvert",       IntegerType()),
])

SCHEMA_VENTES = StructType([
    StructField("id_vente",      IntegerType()),
    StructField("id_temps",      IntegerType()),
    StructField("id_client",     IntegerType()),
    StructField("id_produit",    IntegerType()),
    StructField("id_magasin",    IntegerType()),
    StructField("quantite",      IntegerType()),
    StructField("prix_unitaire", DoubleType()),
    StructField("remise_pct",    DoubleType()),
    StructField("prix_vente",    DoubleType()),
    StructField("montant_ht",    DoubleType()),
    StructField("montant_ttc",   DoubleType()),
    StructField("cout_total",    DoubleType()),
    StructField("marge_brute",   DoubleType()),
    StructField("canal_vente",   StringType()),
])

# ─────────────────────────────────────────────────────────────
# 3. Chargement et nettoyage des données
# ─────────────────────────────────────────────────────────────

RAW_PATH = "/opt/raw-data/"

def load_raw(spark: SparkSession, table: str, schema: StructType):
    print(f"  📂 Lecture {table}...")
    df = (
        spark.read.format("csv")
        .option("header", "true")
        .schema(schema)
        .load(f"{RAW_PATH}{table}.csv")
    )
    print(f"     → {df.count():,} lignes")
    return df

def clean_dim_temps(df):
    return (df
        .withColumn("date", F.to_date("date", "yyyy-MM-dd"))
        .dropDuplicates(["id_temps"])
        .filter(F.col("id_temps").isNotNull())
    )

def clean_dim_produit(df):
    return (df
        .dropDuplicates(["id_produit"])
        .filter(F.col("prix_unitaire") > 0)
        .filter(F.col("cout_unitaire") > 0)
        .withColumn("taux_marge", F.round("taux_marge", 4))
    )

def clean_dim_client(df):
    return (df
        .dropDuplicates(["id_client"])
        .withColumn("date_inscription", F.to_date("date_inscription", "yyyy-MM-dd"))
        .filter(F.col("age").between(16, 100))
    )

def clean_dim_magasin(df):
    return (df
        .dropDuplicates(["id_magasin"])
        .filter(F.col("surface_m2") > 0)
    )

def clean_fact_ventes(df):
    return (df
        .dropDuplicates(["id_vente"])
        .filter(F.col("montant_ht") > 0)
        .filter(F.col("quantite") > 0)
        .filter(F.col("remise_pct").between(0, 1))
        .withColumn("taux_marge_reel",
            F.round((F.col("montant_ht") - F.col("cout_total")) / F.col("montant_ht"), 4))
    )

# ─────────────────────────────────────────────────────────────
# 4. Écriture dans le Data Warehouse (Parquet + HMS)
# ─────────────────────────────────────────────────────────────

WAREHOUSE = "/opt/warehouse/"

def create_database(spark: SparkSession):
    spark.sql("CREATE DATABASE IF NOT EXISTS ventes_dw "
              "LOCATION '/opt/warehouse/ventes_dw/'")
    spark.sql("USE ventes_dw")
    print("  ✓ Base de données ventes_dw créée")

def write_dim(df, table_name: str, partition_col: str = None):
    print(f"  💾 Écriture {table_name}...")
    writer = (
        df.write
        .format("parquet")
        .mode("overwrite")
        .option("compression", "snappy")
        .option("path", f"{WAREHOUSE}ventes_dw/{table_name}/")
    )
    if partition_col:
        writer = writer.partitionBy(partition_col)
    writer.saveAsTable(f"ventes_dw.{table_name}")
    print(f"     ✓ {table_name} enregistrée dans HMS")

def write_fact(df):
    print("  💾 Écriture fact_ventes (partitionnée par année/mois)...")

    # Ajout des colonnes de partition depuis id_temps
    df_part = (
        df
        .withColumn("annee",   (F.col("id_temps") / 10000).cast("int"))
        .withColumn("mois",    ((F.col("id_temps") % 10000) / 100).cast("int"))
    )

    (
        df_part.write
        .format("parquet")
        .mode("overwrite")
        .option("compression", "snappy")
        .option("path", f"{WAREHOUSE}ventes_dw/fact_ventes/")
        .partitionBy("annee", "mois")
        .saveAsTable("ventes_dw.fact_ventes")
    )
    print("     ✓ fact_ventes partitionnée (annee/mois) et enregistrée dans HMS")

# ─────────────────────────────────────────────────────────────
# 5. Cube OLAP — Tables agrégées pré-calculées
# ─────────────────────────────────────────────────────────────

def build_cube_olap(spark: SparkSession):
    """
    Construit 4 niveaux d'agrégation (cubes OLAP) :
      - cube_mensuel_categorie : CA + volume par mois × catégorie
      - cube_mensuel_region    : CA par mois × région
      - cube_mensuel_canal     : CA par mois × canal de vente
      - cube_produit_top       : Classement des produits (CA annuel)
    """
    print("\n📊 Construction du cube OLAP...")

    spark.sql("DROP TABLE IF EXISTS ventes_dw.cube_mensuel_categorie")
    spark.sql("""
        CREATE TABLE ventes_dw.cube_mensuel_categorie
        USING parquet
        LOCATION '/opt/warehouse/ventes_dw/cube_mensuel_categorie/'
        AS
        SELECT
            t.annee,
            t.mois,
            t.mois_nom,
            t.trimestre,
            t.saison,
            p.categorie,
            p.sous_categorie,
            COUNT(DISTINCT f.id_vente)        AS nb_transactions,
            SUM(f.quantite)                   AS volume_ventes,
            ROUND(SUM(f.montant_ht), 2)       AS ca_ht,
            ROUND(SUM(f.montant_ttc), 2)      AS ca_ttc,
            ROUND(SUM(f.marge_brute), 2)      AS marge_brute,
            ROUND(AVG(f.montant_ht), 2)       AS panier_moyen,
            ROUND(AVG(f.remise_pct) * 100, 2) AS remise_moyenne_pct,
            ROUND(SUM(f.marge_brute) / NULLIF(SUM(f.montant_ht), 0) * 100, 2) AS taux_marge_pct
        FROM ventes_dw.fact_ventes f
        JOIN ventes_dw.dim_temps   t ON f.id_temps   = t.id_temps
        JOIN ventes_dw.dim_produit p ON f.id_produit = p.id_produit
        GROUP BY 1,2,3,4,5,6,7
    """)
    print("  ✓ cube_mensuel_categorie")

    spark.sql("DROP TABLE IF EXISTS ventes_dw.cube_mensuel_region")
    spark.sql("""
        CREATE TABLE ventes_dw.cube_mensuel_region
        USING parquet
        LOCATION '/opt/warehouse/ventes_dw/cube_mensuel_region/'
        AS
        SELECT
            t.annee,
            t.mois,
            t.trimestre,
            c.region,
            m.type_magasin,
            COUNT(DISTINCT f.id_vente)   AS nb_transactions,
            COUNT(DISTINCT f.id_client)  AS nb_clients_actifs,
            ROUND(SUM(f.montant_ht), 2)  AS ca_ht,
            ROUND(AVG(f.montant_ht), 2)  AS panier_moyen,
            ROUND(SUM(f.marge_brute), 2) AS marge_brute
        FROM ventes_dw.fact_ventes f
        JOIN ventes_dw.dim_temps    t ON f.id_temps   = t.id_temps
        JOIN ventes_dw.dim_client   c ON f.id_client  = c.id_client
        JOIN ventes_dw.dim_magasin  m ON f.id_magasin = m.id_magasin
        GROUP BY 1,2,3,4,5
    """)
    print("  ✓ cube_mensuel_region")

    spark.sql("DROP TABLE IF EXISTS ventes_dw.cube_mensuel_canal")
    spark.sql("""
        CREATE TABLE ventes_dw.cube_mensuel_canal
        USING parquet
        LOCATION '/opt/warehouse/ventes_dw/cube_mensuel_canal/'
        AS
        SELECT
            t.annee,
            t.mois,
            f.canal_vente,
            COUNT(DISTINCT f.id_vente)   AS nb_transactions,
            ROUND(SUM(f.montant_ht), 2)  AS ca_ht,
            ROUND(AVG(f.montant_ht), 2)  AS panier_moyen,
            ROUND(SUM(f.marge_brute), 2) AS marge_brute
        FROM ventes_dw.fact_ventes f
        JOIN ventes_dw.dim_temps t ON f.id_temps = t.id_temps
        GROUP BY 1,2,3
    """)
    print("  ✓ cube_mensuel_canal")

    spark.sql("DROP TABLE IF EXISTS ventes_dw.cube_produit_top")
    spark.sql("""
        CREATE TABLE ventes_dw.cube_produit_top
        USING parquet
        LOCATION '/opt/warehouse/ventes_dw/cube_produit_top/'
        AS
        SELECT
            t.annee,
            p.id_produit,
            p.nom_produit,
            p.categorie,
            p.sous_categorie,
            p.marque,
            COUNT(DISTINCT f.id_vente)   AS nb_transactions,
            SUM(f.quantite)              AS volume_ventes,
            ROUND(SUM(f.montant_ht), 2)  AS ca_ht,
            ROUND(SUM(f.marge_brute), 2) AS marge_brute,
            ROUND(SUM(f.marge_brute) / NULLIF(SUM(f.montant_ht), 0) * 100, 2) AS taux_marge_pct,
            RANK() OVER (PARTITION BY t.annee ORDER BY SUM(f.montant_ht) DESC) AS rang_ca
        FROM ventes_dw.fact_ventes f
        JOIN ventes_dw.dim_temps   t ON f.id_temps   = t.id_temps
        JOIN ventes_dw.dim_produit p ON f.id_produit = p.id_produit
        GROUP BY 1,2,3,4,5,6
    """)
    print("  ✓ cube_produit_top")

# ─────────────────────────────────────────────────────────────
# 6. KPIs de synthèse
# ─────────────────────────────────────────────────────────────

def compute_kpis(spark: SparkSession):
    print("\n📈 Calcul des KPIs de synthèse...")

    # KPI global par année
    kpis = spark.sql("""
        SELECT
            t.annee,
            COUNT(DISTINCT f.id_vente)                    AS nb_transactions,
            COUNT(DISTINCT f.id_client)                   AS nb_clients_actifs,
            ROUND(SUM(f.montant_ht), 0)                   AS ca_ht_total,
            ROUND(AVG(f.montant_ht), 2)                   AS panier_moyen,
            ROUND(SUM(f.marge_brute), 0)                  AS marge_brute_totale,
            ROUND(SUM(f.marge_brute)/SUM(f.montant_ht)*100, 2) AS taux_marge_pct,
            ROUND(AVG(f.remise_pct)*100, 2)               AS remise_moyenne_pct
        FROM ventes_dw.fact_ventes f
        JOIN ventes_dw.dim_temps t ON f.id_temps = t.id_temps
        GROUP BY t.annee
        ORDER BY t.annee
    """)

    print("\n  ┌─────────────────────── KPIs Annuels ───────────────────────┐")
    kpis.show(truncate=False)

    # Croissance YoY
    growth = spark.sql("""
        WITH ca_annuel AS (
            SELECT t.annee, SUM(f.montant_ht) AS ca
            FROM ventes_dw.fact_ventes f
            JOIN ventes_dw.dim_temps t ON f.id_temps = t.id_temps
            GROUP BY t.annee
        )
        SELECT
            annee,
            ROUND(ca, 0) AS ca_ht,
            LAG(ca) OVER (ORDER BY annee) AS ca_annee_prec,
            ROUND((ca - LAG(ca) OVER (ORDER BY annee)) /
                   LAG(ca) OVER (ORDER BY annee) * 100, 2) AS croissance_pct
        FROM ca_annuel
        ORDER BY annee
    """)
    print("  ┌─────────────────────── Croissance YoY ─────────────────────┐")
    growth.show(truncate=False)

    return kpis

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  🧊 Cube Analytique — Pipeline ETL Spark SQL")
    print("=" * 65)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # ── Étape 1 : Chargement ──────────────────────────────────
    print("\n[1/5] Chargement des données brutes...")
    df_temps    = load_raw(spark, "dim_temps",    SCHEMA_TEMPS)
    df_produit  = load_raw(spark, "dim_produit",  SCHEMA_PRODUIT)
    df_client   = load_raw(spark, "dim_client",   SCHEMA_CLIENT)
    df_magasin  = load_raw(spark, "dim_magasin",  SCHEMA_MAGASIN)
    df_ventes   = load_raw(spark, "fact_ventes",  SCHEMA_VENTES)

    # ── Étape 2 : Nettoyage ──────────────────────────────────
    print("\n[2/5] Nettoyage et validation...")
    df_temps    = clean_dim_temps(df_temps)
    df_produit  = clean_dim_produit(df_produit)
    df_client   = clean_dim_client(df_client)
    df_magasin  = clean_dim_magasin(df_magasin)
    df_ventes   = clean_fact_ventes(df_ventes)

    # ── Étape 3 : Base de données ────────────────────────────
    print("\n[3/5] Création de la base de données...")
    create_database(spark)

    # ── Étape 4 : Écriture du schéma en étoile ───────────────
    print("\n[4/5] Écriture du schéma en étoile (Parquet + HMS)...")
    write_dim(df_temps,   "dim_temps")
    write_dim(df_produit, "dim_produit")
    write_dim(df_client,  "dim_client")
    write_dim(df_magasin, "dim_magasin")
    write_fact(df_ventes)

    # ── Étape 5 : Cube OLAP ───────────────────────────────────
    print("\n[5/5] Construction du cube OLAP...")
    build_cube_olap(spark)
    compute_kpis(spark)

    print("\n" + "=" * 65)
    print("  ✅ Pipeline ETL terminé avec succès !")
    print("  📍 Tables disponibles dans ventes_dw :")
    spark.sql("SHOW TABLES IN ventes_dw").show(truncate=False)
    print("=" * 65)

    spark.stop()

if __name__ == "__main__":
    main()
