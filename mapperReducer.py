import subprocess, os

HADOOP = os.environ["HADOOP_HOME"]
JAR = f"{HADOOP}/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar"
INPUT = "/input_dir/christmascarol.txt"
TMP = "/output/mapreduce_tmp"
FINAL = "/output/mapreduce_output.txt"

def hdfs(*args):
    return subprocess.run(["hdfs", "dfs", *args],
                          capture_output=True, text=True)

# ryd op efter tidligere kørsler
hdfs("-rm", "-r", "-f", TMP)
hdfs("-rm", "-r", "-f", FINAL)

# EXTRACT + TRANSFORM — MapReduce-jobbet gør arbejdet
print("Starter MapReduce-job...")
job = subprocess.run([
    "hadoop", "jar", JAR,
    "-D", "mapreduce.job.reduces=1",
    "-files", "mapper.py,reducer.py",
    "-input", INPUT,
    "-output", TMP,
    "-mapper", "python3 mapper.py",
    "-reducer", "python3 reducer.py",
])
if job.returncode != 0:
    raise SystemExit("MapReduce-jobbet fejlede")

# hent reducerens output
raw = hdfs("-cat", f"{TMP}/part-00000").stdout

rows = []
total = 0
for line in raw.strip().splitlines():
    word, count, pos = line.split("\t")
    rows.append((int(pos), word, int(count)))
    total += int(count)

# sortér efter første forekomst i teksten, som i batch-øvelsen
rows.sort()

lines = [f"Antal ord ialt: {total}"]
for i, (_, word, count) in enumerate(rows, start=1):
    lines.append(f"{i} {word}: {count}")

# LOAD — skriv resultatet tilbage til HDFS
with open("/tmp/mr_output.txt", "w") as f:
    f.write("\n".join(lines))
hdfs("-put", "-f", "/tmp/mr_output.txt", FINAL)

print(f"Antal ord ialt: {total}")
for line in lines[1:11]:
    print(line)
print(f"\nResultat gemt i {FINAL}")