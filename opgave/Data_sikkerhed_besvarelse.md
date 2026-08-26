# Data sikkerhed og transport

## 1. GDPR

EU's forordning fra 2018, der beskytter borgeres personoplysninger og sikrer,
at data behandles lovligt og gennemsigtigt. Personen ejer sine data —
virksomheden låner dem til et bestemt formål.

| Nr. | Rettighed | Beskrivelse | Artikel |
|-----|-----------|-------------|---------|
| 1 | Ret til oplysning | Man skal af sig selv have at vide, at data indsamles, af hvem, til hvilket formål og hvor længe | Art. 13-14 |
| 2 | Ret til indsigt | Man kan bede om at få at vide, om der behandles data om én, og få en kopi | Art. 15 |
| 3 | Ret til berigtigelse | Forkerte oplysninger skal rettes, ufuldstændige skal suppleres | Art. 16 |
| 4 | Ret til sletning | Data skal slettes, når formålet er opfyldt eller samtykket trækkes tilbage | Art. 17 |
| 5 | Ret til begrænsning | Data må opbevares, men ikke bruges, mens en tvist afklares | Art. 18 |
| 6 | Ret til dataportabilitet | Man kan få sine data udleveret i et maskinlæsbart format og tage dem med | Art. 20 |
| 7 | Ret til indsigelse | Man kan protestere mod behandlingen. Ved markedsføring skal den altid stoppe | Art. 21 |
| 8 | Ret vedr. automatiske afgørelser | Man må ikke afgøres udelukkende af en algoritme og har ret til et menneske | Art. 22 |
| 9 | Ret til at klage | Man kan klage til Datatilsynet | Art. 77 |

Databrud skal anmeldes til Datatilsynet inden 72 timer. Bøde op til 20 mio.
euro eller 4 % af den globale omsætning.

## 2. Anonymisering

Pointen er at kunne bruge data uden at bruge personen. Analysen har brug for
mønstre — hvor mange over 30 fordelt på land og køn — ikke for at vide hvem.

| Teknik | Formål |
|--------|--------|
| Kryptering | Gøre data ulæselige for uvedkommende under transport og opbevaring, men fuldt læsbare for den, der har nøglen. Beskytter data, men fjerner ikke identificerbarheden — er stadig personoplysninger |
| Pseudonymisering | Erstatte navn, e-mail og CPR med et kunstigt ID, så data kan analyseres uden at afsløre identiteten. Kan kobles tilbage via en separat mapping-tabel — er stadig personoplysninger |
| Anonymisering | Fjerne identificerbarheden uigenkaldeligt. Ingen nøgle og ingen mapping findes. Resultatet er ikke personoplysninger, og GDPR gælder ikke |

Huskeregel: kryptering er en låst dør, pseudonymisering er et kodenavn,
anonymisering er at brænde listen.

## 3. Databeskyttelsesloven

Den danske lov fra 2018, der supplerer og præciserer GDPR.

Den er nødvendig, fordi GDPR indeholder omkring 70 åbningsklausuler — steder,
hvor forordningen med vilje overlader detaljerne til medlemslandene. GDPR
sætter rammen, den danske lov udfylder hullerne:

- Hvornår private må behandle CPR-numre (§ 11) — et rent dansk fænomen
- Aldersgrænsen for samtykke, som Danmark satte til 13 år
- Hvor længe en arbejdsgiver må gemme ansøgerdata
- At Datatilsynet er tilsynsmyndighed og kan udstede bøder

Ved konflikt vinder GDPR, fordi en forordning står over national lov.

## 4. De to pipelines

Begge henter 100 syntetiske profiler fra randomuser.me og filtrerer personer
over 30 år. **requests** er modulet, der giver kryptering under datatransport,
fordi det bruger HTTPS (TLS) og validerer serverens certifikat.

**pseudoPipeline.py — pseudonymisering**
Navn, e-mail og telefon erstattes af et ID lavet med HMAC-SHA256.
Alder, køn og land beholdes. Der laves en krypteret mapping-fil, så data
kan kobles tilbage til personen.

**anonPipeline.py — anonymisering**
Alle identifikatorer fjernes helt. Præcis alder generaliseres til 10-års
intervaller, og grupper med under 3 personer undertrykkes (k-anonymitet),
så ingen kan udpeges. Der laves ingen mapping-fil.

Forskellen kan ses i filsystemet: kun det første script efterlader
`mapping_pseudonym.enc`. Det er derfor pseudonymiseret data stadig er
personoplysninger, mens anonymiseret data ikke er.

## 5. Kryptering

**Valgt: symmetrisk** — Fernet fra Pythons cryptography-modul (AES-128 med
HMAC-SHA256 til integritetskontrol). Begrundelsen er, at det er samme maskine
og samme script, der både krypterer og dekrypterer filen. Der er ingen
modtager, som skal have en nøgle udleveret — og det er netop dét problem,
asymmetrisk kryptering løser.

**Forskellen mellem kryptering og hashing**

| | Kryptering | Hashing |
|---|---|---|
| Vej | To-vejs, kan dekrypteres | Én-vejs, kan ikke vendes om |
| Nøgle | Kræver nøgle | Kræver ingen (medmindre HMAC) |
| Formål | Fortrolighed — skjule data, man skal bruge igen | Integritet — bevise at noget er uændret |
| Eksempel | Gemme en datafil sikkert | Gemme adgangskoder |

Adgangskoder hashes netop, fordi det ikke kan vendes om: systemet behøver ikke
kende koden, kun kunne genkende den.

**Data udlagt på nettet via API — symmetrisk eller asymmetrisk?**

Asymmetrisk. Problemet med symmetrisk er nøgledistributionen: alle klienter
skulle have den samme nøgle, og så snart den er delt med hundrede kunder, er
den reelt offentlig. Ét læk kompromitterer hele datasættet, og nøglen kan ikke
trækkes tilbage fra én kunde uden at kryptere alt om.

Med asymmetrisk har hver modtager sit eget nøglepar. Serveren krypterer med
modtagerens offentlige nøgle, som gerne må ligge frit fremme, og kun den
private nøgle kan låse op. Mister én kunde sin nøgle, rammer det kun den ene.

I praksis kombineres de: asymmetrisk bruges til at udveksle en midlertidig
symmetrisk sessionsnøgle, og selve datastrømmen krypteres symmetrisk, fordi
det er hurtigere. Det er præcis sådan TLS fungerer — altså det, der sker
automatisk, når scriptet henter data over `https://`.

**Hvor krypteres og dekrypteres der i koden**

Kryptering sker i `extract()`, lige efter API-kaldet:
```python
open(RAW_ENC, "wb").write(Fernet(noegle).encrypt(svar.content))
```

Dekryptering sker i `main()`, lige før databehandlingen:
```python
raadata = json.loads(Fernet(noegle).decrypt(open(RAW_ENC, "rb").read()))
```

**Hvordan gemmes krypteringsnøglen, og i hvilket format?**

Nøglen gemmes som filen `secret.key` i brugerens hjemmemappe med rettigheden
`0o600` — kun ejeren kan læse den. Linjen i koden er `os.chmod(KEY_FILE, 0o600)`.

Formatet er en Fernet-nøgle: 32 tilfældige bytes, hvor de første 16 bruges til
signering og de sidste 16 til kryptering. De er kodet som url-safe base64,
hvilket giver en streng på 44 ASCII-tegn, der slutter med `=`.

Filen er udelukket fra versionsstyring via `.gitignore`. En nøgle i et git-repo
bliver liggende i historikken for evigt, også hvis man sletter filen bagefter.
I produktion ville man bruge en key vault eller en miljøvariabel i stedet for
en fil på disken.

Vis den med:
```
ls -l ~/secret.key
wc -c ~/secret.key
```
