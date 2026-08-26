#!/usr/bin/env python3
import sys, os, re

# hvor i filen dette split begynder — bruges til at bevare ordenes rækkefølge
offset = int(os.environ.get("mapreduce_map_input_start", 0))

for line in sys.stdin:
    for match in re.finditer(r"[a-z']+", line.lower()):
        pos = offset + match.start()
        print(f"{match.group()}\t1\t{pos}")
    offset += len(line)