import json, os
from collections import Counter
import requests
from cryptography.fernet import Fernet

API_URL = "https://randomuser.me/api/?results=100"
MIN_ALDER = 30
K = 3                                    # k-anonymitet
KEY_FILE = os.path.expanduser("~/secret.key")
RAW_ENC = os.path.expanduser("~/raw_users.enc")
OUTPUT_TXT = os.path.expanduser("~/output_anonymiseret.txt")

def hent_noegle():
    if not os.path.exists(KEY_FILE):
        open(KEY_FILE, "wb").write(Fernet.generate_key())
        os.chmod(KEY_FILE, 0o600)
    return open(KEY_FILE, "rb").read()

# EXTRACT — HTTPS giver kryptering under transport
def extract(noegle):
    svar = requests.get(API_URL, timeout=30, verify=True)
    svar.raise_for_status()
    print(f"EXTRACT: hentet {len(svar.content)} bytes over HTTPS")
    open(RAW_ENC, "wb").write(Fernet(noegle).encrypt(svar.content))
    print("  raadata gemt KRYPTERET i raw_users.enc")

# Generalisering: 34 -> "30-39". Den praecise alder gaar tabt.
def aldersgruppe(alder):
    start = (alder // 10) * 10
    return f"{start}-{start + 9}"

# TRANSFORM — fjern identifikatorer, generaliser, undertryk smaa grupper
def transform(raadata):
    poster = []
    for p in raadata["results"]:
        if p["dob"]["age"] <= MIN_ALDER:
            continue
        poster.append((p["location"]["country"],
                       p["gender"],
                       aldersgruppe(p["dob"]["age"])))

    print(f"TRANSFORM: {len(poster)} personer over {MIN_ALDER} aar")
    print("  navn, e-mail, telefon og adresse fjernet helt")
    print("  praecis alder erstattet af 10-aars interval")

    grupper = Counter(poster)
    beholdt = {g: n for g, n in grupper.items() if n >= K}
    fjernet = {g: n for g, n in grupper.items() if n < K}
    print(f"  K-anonymitet (K={K}): {len(fjernet)} gruppe(r) undertrykt")
    return beholdt, fjernet, len(poster)

# LOAD — skriv det aggregerede resultat
def main():
    noegle = hent_noegle()
    extract(noegle)
    raadata = json.loads(Fernet(noegle).decrypt(open(RAW_ENC, "rb").read()))
    beholdt, fjernet, antal = transform(raadata)

    i_resultat = sum(beholdt.values())
    linjer = [
        "ANONYMISERET DATASAET",
        f"Personer efter filter: {antal}",
        f"Personer i resultatet: {i_resultat}",
        f"Undertrykt af hensyn til K-anonymitet (K={K}): {antal - i_resultat}",
        "",
        "Ingen mapping-fil findes. Resultatet kan ikke foeres tilbage",
        "til den enkelte person.",
        "",
    ]
    for (land, koen, gruppe), n in sorted(beholdt.items(), key=lambda x: -x[1]):
        linjer.append(f"{land:<26}{koen:<10}{gruppe:<12}{n}")

    open(OUTPUT_TXT, "w").write("\n".join(linjer))
    print("LOAD: skrevet til output_anonymiseret.txt\n")
    print(open(OUTPUT_TXT).read())

main()