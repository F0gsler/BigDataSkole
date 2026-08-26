# visualisering.py - VISUALISERINGSMODUL
# Tre metoder, der hver modtager et pandas DataFrame som parameter og
# gemmer det faerdige diagram direkte paa HDFS.
# Billedet skrives via en pipe til 'hdfs dfs -put -', saa det gaar fra
# hukommelsen direkte i HDFS. Der lander aldrig en PNG paa den lokale disk.

import io
import subprocess

import matplotlib
matplotlib.use("Agg")          # ingen skaerm i WSL - tegn til hukommelsen
import matplotlib.pyplot as plt


# ------------------------------------------------------------------ hjaelper
# Skriver figuren direkte til HDFS uden at roere den lokale disk
def _gem_paa_hdfs(fig, hdfs_sti):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)

    subprocess.run(["hdfs", "dfs", "-rm", "-f", hdfs_sti],
                   capture_output=True)
    p = subprocess.run(["hdfs", "dfs", "-put", "-", hdfs_sti],
                       input=buffer.read(), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode())
    print(f"  Diagram gemt paa HDFS: {hdfs_sti}")


# ------------------------------------------------------------------ 1. scatter
# Sammenhaengen mellem sepal_length (x) og petal_length (y)
def scatter_plot(df, hdfs_sti):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["sepal_length"], df["petal_length"], alpha=0.8)

    ax.set_title("Scatter Plot: Sepal Length vs Petal Length (Iris-setosa)")
    ax.set_xlabel("Sepallaengde (sepal_length)")
    ax.set_ylabel("Kronbladlaengde (petal_length)")
    ax.grid(True, linestyle="--", alpha=0.4)

    _gem_paa_hdfs(fig, hdfs_sti)


# ------------------------------------------------------------------ 2. histogram
# Fordelingen af petal_width i ca. 10 soejler
def histogram(df, hdfs_sti):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(df["petal_width"], bins=10, edgecolor="black")

    ax.set_title("Histogram: Petal Width (Iris-setosa)")
    ax.set_xlabel("Kronbladsbredde (petal_width)")
    ax.set_ylabel("Frekvens")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    _gem_paa_hdfs(fig, hdfs_sti)


# ------------------------------------------------------------------ 3. boxplot
# 2x2 layout med et boxplot for hver af de fire maalinger
def boxplot(df, hdfs_sti):
    kolonner = ["sepal_length", "sepal_width", "petal_length", "petal_width"]

    fig, akser = plt.subplots(2, 2, figsize=(9, 7))
    fig.suptitle("Boxplots af alle numeriske Iris-setosa maalinger",
                 fontsize=13)

    for ax, kolonne in zip(akser.flatten(), kolonner):
        ax.boxplot(df[kolonne])
        ax.set_title(kolonne)
        ax.set_ylabel("Vaerdi (cm)")
        ax.set_xticklabels([kolonne])
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    _gem_paa_hdfs(fig, hdfs_sti)
