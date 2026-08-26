import hashlib, hmac, json, os
import requests
from cryptography.fernet import Fernet

API_URL = "https://randomuser.me/api/?results=100"
MIN_ALDER = 30
KEY_FILE = os.path.expanduser("~/secret.key")
RAW_ENC = os.path.expanduser("~/raw_users.enc")
OUTPUT_TXT = os.path.expanduser("~/output_pseudonymiseret.txt")

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

# HMAC-SHA256: samme e-mail giver samme pseudonym, men kan ikke gættes
def lav_pseudonym(vaerdi, noegle):
    d = hmac.new(noegle, vaerdi.encode(), hashlib.sha256).hexdigest()
    return "PSN-" + d[:16].upper()

# TRANSFORM — filtrér på alder og erstat identifikatorer
def transform(raadata, noegle):
    resultat = []
    for p in raadata["results"]:
        if p["dob"]["age"] <= MIN_ALDER:
            continue
        resultat.append({
            "id": lav_pseudonym(p["email"], noegle),
            "alder": p["dob"]["age"],
            "koen": p["gender"],
            "land": p["location"]["country"],
        })
    print(f"TRANSFORM: {len(resultat)} personer over {MIN_ALDER} aar")
    print("  navn, e-mail og telefon erstattet med pseudonym")
    return resultat

# LOAD — skriv resultatet
def main():
    noegle = hent_noegle()
    extract(noegle)
    raadata = json.loads(Fernet(noegle).decrypt(open(RAW_ENC, "rb").read()))
    resultat = transform(raadata, noegle)

    linjer = [f"Antal personer over {MIN_ALDER}: {len(resultat)}", ""]
    for r in sorted(resultat, key=lambda x: x["alder"]):
        linjer.append(f"{r['id']}  {r['alder']}  {r['koen']}  {r['land']}")
    open(OUTPUT_TXT, "w").write("\n".join(linjer))
    print("LOAD: skrevet til output_pseudonymiseret.txt\n")
    print(open(OUTPUT_TXT).read())

main()