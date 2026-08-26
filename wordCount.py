from pyspark.sql import SparkSession
import re

HDFS = "hdfs://localhost:9000"
INPUT = f"{HDFS}/input_dir/christmascarol.txt"
OUTPUT = f"{HDFS}/output/output.txt"

spark = SparkSession.builder.appName("WordCountBatch").getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("WARN")

# EXTRACT — læs rådata fra HDFS
lines = sc.textFile(INPUT)

# TRANSFORM — rens teksten, tæl ordene, bevar rækkefølgen
words = lines.flatMap(lambda line: re.findall(r"[a-z']+", line.lower()))
total = words.count()

# hvert ord får sin position i teksten med
indexed = words.zipWithIndex().map(lambda p: (p[0], (1, p[1])))

# læg antal sammen, og behold den tidligste position
counted = indexed.reduceByKey(lambda a, b: (a[0] + b[0], min(a[1], b[1])))

# sortér efter første forekomst og nummerér linjerne
ordered = (counted
           .sortBy(lambda kv: kv[1][1])
           .zipWithIndex()
           .map(lambda kv: f"{kv[1] + 1} {kv[0][0]}: {kv[0][1][0]}"))

header = sc.parallelize([f"Antal ord ialt: {total}"])
header.union(ordered).coalesce(1).saveAsTextFile(OUTPUT)

print(f"Antal ord ialt: {total}")
for line in ordered.take(10):
    print(line)

spark.stop()