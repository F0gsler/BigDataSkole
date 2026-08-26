import io
import subprocess

import pandas as pd
import requests
from cryptography.fernet import Fernet
from pyspark.sql import SparkSession
from pyspark.sql.types import (DoubleType, StringType, StructField,
                               StructType)

import visualisering

# ----------------------------------------------------------------- opsætning
CSV_URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/iris.csv"
HDFS = "hdfs://localhost:9000"

RAA_HDFS = "/iris/iris_raw.csv"              # ufiltreret kildedata
KRYPTERET_HDFS = "/iris/iris_setosa.enc"     # transformeret OG krypteret
NOEGLE_HDFS = "/iris/secret.key"

DIAGRAM_SCATTER = "/iris/diagrammer/scatter_plot.png"
DIAGRAM_HISTOGRAM = "/iris/diagrammer/histogram.png"
DIAGRAM_BOXPLOT = "/iris/diagrammer/boxplot.png"

# jbrownlee's iris.csv har INGEN overskriftsrække - vi navngiver selv
SKEMA = StructType([
    StructField("sepal_length", DoubleType(), True),
    StructField("sepal_width", DoubleType(), True),
    StructField("petal_length", DoubleType(), True),
    StructField("petal_width", DoubleType(), True),
    StructField("species", StringType(), True),
])


# ----------------------------------------------------------------- HDFS-hjælp
# Skriver bytes direkte til HDFS via en pipe - ingen lokal fil
def hdfs_skriv(bytes_data, sti):
    subprocess.run(["hdfs", "dfs", "-rm", "-f", sti], capture_output=True)
    p = subprocess.run(["hdfs", "dfs", "-put", "-", sti],
                       input=bytes_data, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode())


# Læser en fil fra HDFS ind i hukommelsen - ingen lokal fil
def hdfs_laes(sti):
    p = subprocess.run(["hdfs", "dfs", "-cat", sti], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode())
    return p.stdout


def hdfs_findes(sti):
    return subprocess.run(["hdfs", "dfs", "-test", "-e", sti],
                          capture_output=True).returncode == 0


# Nøglen gemmes også på HDFS, så intet ligger på PC'en
def hent_nøgle():
    if hdfs_findes(NOEGLE_HDFS):
        return hdfs_laes(NOEGLE_HDFS).strip()
    nøgle = Fernet.generate_key()
    hdfs_skriv(nøgle, NOEGLE_HDFS)
    print(f"  Ny nøgle oprettet på HDFS: {NOEGLE_HDFS}")
    return nøgle


# ----------------------------------------------------------------- EXTRACT
def extract():
    print("EXTRACT: henter iris.csv over HTTPS ...")
    svar = requests.get(CSV_URL, timeout=30, verify=True)
    svar.raise_for_status()
    print(f"  {len(svar.content)} bytes modtaget over TLS")

    # Indholdet sendes direkte videre til HDFS - det rører aldrig disken
    hdfs_skriv(svar.content, RAA_HDFS)
    print(f"  Rådata lagt på HDFS: {RAA_HDFS}\n")


# ----------------------------------------------------------------- TRANSFORM
def transform(spark, nøgle):
    print("TRANSFORM: Spark filtrerer Iris-setosa fra ...")

    # Spark læser DIREKTE fra HDFS - ingen lokal kopi
    df = spark.read.csv(f"{HDFS}{RAA_HDFS}", schema=SKEMA)
    print(f"  {df.count()} rækker læst fra HDFS")

    setosa = df.filter(df.species == "Iris-setosa")
    print(f"  {setosa.count()} rækker tilbage efter filter")

    # Datasættet er lille (50 rækker), så det samles til et pandas
    # DataFrame og serialiseres som CSV før krypteringen
    pdf = setosa.toPandas()
    csv_bytes = pdf.to_csv(index=False).encode("utf-8")

    # ---- KRYPTERING: transformeret data krypteres før det gemmes ----
    krypteret = Fernet(nøgle).encrypt(csv_bytes)
    hdfs_skriv(krypteret, KRYPTERET_HDFS)
    print(f"  Transformeret data KRYPTERET og gemt: {KRYPTERET_HDFS}\n")


# ----------------------------------------------------------------- LOAD
def load(nøgle):
    print("LOAD: henter krypteret fil og laver DataFrame ...")

    krypteret = hdfs_laes(KRYPTERET_HDFS)

    # ---- DEKRYPTERING: sker først her, lige inden diagrammerne tegnes ----
    klartekst = Fernet(nøgle).decrypt(krypteret)
    df = pd.read_csv(io.StringIO(klartekst.decode("utf-8")))
    print(f"  {len(df)} rækker dekrypteret i hukommelsen\n")

    print("VISUALISERING: kalder de tre metoder i modulet ...")
    visualisering.scatter_plot(df, DIAGRAM_SCATTER)
    visualisering.histogram(df, DIAGRAM_HISTOGRAM)
    visualisering.boxplot(df, DIAGRAM_BOXPLOT)
    print()


# ----------------------------------------------------------------- kørsel
def main():
    spark = (SparkSession.builder
             .appName("IrisVisualisering")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    nøgle = hent_nøgle()
    extract()
    transform(spark, nøgle)
    load(nøgle)

    print("=" * 55)
    print("Diagrammer på HDFS:")
    subprocess.run(["hdfs", "dfs", "-ls", "/iris/diagrammer"])

    spark.stop()


if __name__ == "__main__":
    main()