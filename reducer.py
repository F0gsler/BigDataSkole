#!/usr/bin/env python3
import sys

current = None
count = 0
first = None

for line in sys.stdin:
    word, one, pos = line.strip().split("\t")
    pos = int(pos)
    if word == current:
        count += 1
        first = min(first, pos)
    else:
        if current is not None:
            print(f"{current}\t{count}\t{first}")
        current, count, first = word, 1, pos

if current is not None:
    print(f"{current}\t{count}\t{first}")