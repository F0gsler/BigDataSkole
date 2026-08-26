# main.py - ETL PIPELINE MED KRYPTERING
# Extract   : henter iris.csv over HTTPS og sender den direkte videre til
#             HDFS gennem en pipe. Filen lander aldrig paa den lokale disk.
# Transform : Spark laeser raadata fra HDFS, filtrerer Iris-setosa fra og
#             krypterer resultatet, foer det skrives tilbage til HDFS.
# Load      : den krypterede fil laeses fra HDFS, dekrypteres i hukommelsen,
#             bliver til et DataFrame og sendes til visualiseringsmodulet.
# Hele vejen igennem ligger data i HDFS - PC'ens filsystem beroeres ikke.

import io
import subprocess

import pandas as pd
import requests
from cryptography.fernet import Fernet
from pyspark.sql import SparkSession
from pyspark.sql.types import (DoubleType, StringType, StructField,
                               StructType)

import visualisering

# ----------------------------------------------------------------- opsaetning
CSV_URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/iris.csv"
HDFS = "hdfs://localhost:9000"

RAA_HDFS = "/iris/iris_raw.csv"              # ufiltreret kildedata
KRYPTERET_HDFS = "/iris/iris_setosa.enc"     # transformeret OG krypteret
NOEGLE_HDFS = "/iris/secret.key"

DIAGRAM_SCATTER = "/iris/diagrammer/scatter_plot.png"
DIAGRAM_HISTOGRAM = "/iris/diagrammer/histogram.png"
DIAGRAM_BOXPLOT = "/iris/diagrammer/boxplot.png"

# jbrownlee's iris.csv har INGEN overskriftsraekke - vi navngiver selv
SKEMA = StructType([
    StructField("sepal_length", DoubleType(), True),
    StructField("sepal_width", DoubleType(), True),
    StructField("petal_length", DoubleType(), True),
    StructField("petal_width", DoubleType(), True),
    StructField("species", StringType(), True),
])


# ----------------------------------------------------------------- HDFS-hjaelp
# Skriver bytes direkte til HDFS via en pipe - ingen lokal fil
def hdfs_skriv(bytes_data, sti):
    subprocess.run(["hdfs", "dfs", "-rm", "-f", sti], capture_output=True)
    p = subprocess.run(["hdfs", "dfs", "-put", "-", sti],
                       input=bytes_data, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode())


# Laeser en fil fra HDFS ind i hukommelsen - ingen lokal fil
def hdfs_laes(sti):
    p = subprocess.run(["hdfs", "dfs", "-cat", sti], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode())
    return p.stdout


def hdfs_findes(sti):
    return subprocess.run(["hdfs", "dfs", "-test", "-e", sti],
                          capture_output=True).returncode == 0


# Noeglen gemmes ogsaa paa HDFS, saa intet ligger paa PC'en
def hent_noegle():
    if hdfs_findes(NOEGLE_HDFS):
        return hdfs_laes(NOEGLE_HDFS).strip()
    noegle = Fernet.generate_key()
    hdfs_skriv(noegle, NOEGLE_HDFS)
    print(f"  Ny noegle oprettet paa HDFS: {NOEGLE_HDFS}")
    return noegle


# ----------------------------------------------------------------- EXTRACT
def extract():
    print("EXTRACT: henter iris.csv over HTTPS ...")
    svar = requests.get(CSV_URL, timeout=30, verify=True)
    svar.raise_for_status()
    print(f"  {len(svar.content)} bytes modtaget over TLS")

    # Indholdet sendes direkte videre til HDFS - det roerer aldrig disken
    hdfs_skriv(svar.content, RAA_HDFS)
    print(f"  Raadata lagt paa HDFS: {RAA_HDFS}\n")


# ----------------------------------------------------------------- TRANSFORM
def transform(spark, noegle):
    print("TRANSFORM: Spark filtrerer Iris-setosa fra ...")

    # Spark laeser DIREKTE fra HDFS - ingen lokal kopi
    df = spark.read.csv(f"{HDFS}{RAA_HDFS}", schema=SKEMA)
    print(f"  {df.count()} raekker laest fra HDFS")

    setosa = df.filter(df.species == "Iris-setosa")
    print(f"  {setosa.count()} raekker tilbage efter filter")

    # Datasaettet er lille (50 raekker), saa det samles til et pandas
    # DataFrame og serialiseres som CSV foer krypteringen
    pdf = setosa.toPandas()
    csv_bytes = pdf.to_csv(index=False).encode("utf-8")

    # ---- KRYPTERING: transformeret data krypteres foer det gemmes ----
    krypteret = Fernet(noegle).encrypt(csv_bytes)
    hdfs_skriv(krypteret, KRYPTERET_HDFS)
    print(f"  Transformeret data KRYPTERET og gemt: {KRYPTERET_HDFS}\n")


# ----------------------------------------------------------------- LOAD
def load(noegle):
    print("LOAD: henter krypteret fil og laver DataFrame ...")

    krypteret = hdfs_laes(KRYPTERET_HDFS)

    # ---- DEKRYPTERING: sker foerst her, lige inden diagrammerne tegnes ----
    klartekst = Fernet(noegle).decrypt(krypteret)
    df = pd.read_csv(io.StringIO(klartekst.decode("utf-8")))
    print(f"  {len(df)} raekker dekrypteret i hukommelsen\n")

    print("VISUALISERING: kalder de tre metoder i modulet ...")
    visualisering.scatter_plot(df, DIAGRAM_SCATTER)
    visualisering.histogram(df, DIAGRAM_HISTOGRAM)
    visualisering.boxplot(df, DIAGRAM_BOXPLOT)
    print()


# ----------------------------------------------------------------- koersel
def main():
    spark = (SparkSession.builder
             .appName("IrisVisualisering")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    noegle = hent_noegle()
    extract()
    transform(spark, noegle)
    load(noegle)

    print("=" * 55)
    print("Diagrammer paa HDFS:")
    subprocess.run(["hdfs", "dfs", "-ls", "/iris/diagrammer"])

    spark.stop()


if __name__ == "__main__":
    main()
