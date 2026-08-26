import re
import time
import subprocess
from pyspark.sql import SparkSession

HDFS = "hdfs://localhost:9000"
WATCH_DIR = "/input_dir"
OUTPUT_DIR = "/output"
INTERVAL = 10          # sekunder mellem hvert tjek
PROCESS_EXISTING = False   # True = tæl også filer, der lå der i forvejen

spark = SparkSession.builder.appName("WordCountRealtime").getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("ERROR")


def list_txt_files():
    """Spørg HDFS hvilke .txt-filer der ligger i mappen lige nu."""
    result = subprocess.run(
        ["hdfs", "dfs", "-ls", WATCH_DIR],
        capture_output=True, text=True
    )
    files = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[-1].endswith(".txt"):
            files.add(parts[-1])
    return files


def word_count(path):
    """Samme ETL-pipeline som i batch-øvelsen."""
    name = path.split("/")[-1].replace(".txt", "")
    out = f"{HDFS}{OUTPUT_DIR}/output.txt"

    # EXTRACT
    lines = sc.textFile(f"{HDFS}{path}")

    # TRANSFORM
    words = lines.flatMap(lambda l: re.findall(r"[a-z']+", l.lower()))
    total = words.count()
    indexed = words.zipWithIndex().map(lambda p: (p[0], (1, p[1])))
    counted = indexed.reduceByKey(lambda a, b: (a[0] + b[0], min(a[1], b[1])))
    ordered = (counted
               .sortBy(lambda kv: kv[1][1])
               .zipWithIndex()
               .map(lambda kv: f"{kv[1] + 1} {kv[0][0]}: {kv[0][1][0]}"))

    # LOAD
    subprocess.run(["hdfs", "dfs", "-rm", "-r", "-f", out],
                   capture_output=True)
    header = sc.parallelize([f"Antal ord ialt: {total}"])
    header.union(ordered).coalesce(1).saveAsTextFile(out)

    print(f"  Antal ord ialt: {total}")
    print(f"  Resultat gemt i {OUTPUT_DIR}/{name}_output.txt")


seen = set() if PROCESS_EXISTING else list_txt_files()
print(f"Overvåger {WATCH_DIR} — tjekker hvert {INTERVAL}. sekund. Stop med Ctrl+C.")
if seen:
    print(f"Ignorerer {len(seen)} fil(er), der lå der i forvejen.")

try:
    while True:
        current = list_txt_files()
        for path in sorted(current - seen):
            print(f"\nNy fil fundet: {path}")
            try:
                word_count(path)
            except Exception as e:
                print(f"  Fejl under behandling: {e}")
            seen.add(path)
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print("\nOvervågning stoppet.")
    spark.stop()    