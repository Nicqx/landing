# Pandemic LAB próbacsempe – távoli HTTPS használat és kontrollált üzembe helyezés

## Mit csinál ez a csempe?

A nyitóoldalon két új csempe szerepel:

- **Pandemic**: `/pandemic/` – a normál játékszoba.
- **🧪 Pandemic – LAB próba**: `/pandemic/#lab-preview` –
  közvetlenül az ideiglenes LAB-próbaszoba létrehozó
  felületére mutat.

A `#lab-preview` csak **böngészőoldali fragment**, nem
új ingress vagy API. A Pandemic felületen azonos
`id="lab-preview"` szakasz található.

A Pandemic alkalmazás változása biztosítja, hogy
ha már van tárolt normál játékoshely a
`sessionStorage`-ban, a direkt LAB-link ne
azt töltse be automatikusan. A régi játékoshely
megmarad, normál `/pandemic/` linkkel
újra folytatható. A LAB-próba az eredeti
képernyőn **nem indul el kattintás nélkül**.

## Biztonsági korlátok

- A landing **publikus kezdőoldal**; a csempe
  **nem titok**, és nem tekinthető hitelesítésnek.
- A Pandemic meglévő `PANDEMIC_ACCESS_MODE=invite`
  hozzáférési kapuja **a HTML-re, statikus
  JavaScriptre, API-ra és WebSocket-kapcsolatokra**
  is vonatkozik. Meghívó nélkül a `/pandemic/`
  továbbra **401** választ ad. A meghívós
  munkamenet ugyanazon eszközön a korábban
  beállított szabályok szerint érvényes.
- A LAB-próba **14 szintetikus** szekvenciakártyát
  használ, memóriában él, nem mentődik az éles
  Redis-szobatárolóba, és kiszolgáló-újraindításkor
  törlődik. A lejárati idő 6 óra lehet, ha
  már nincs aktív kapcsolat.
- A privát, beszkennelt fizikai LAB-katalógus
  nem kerül GitHubra, a Docker image-be
  vagy a Kubernetes Deploymentbe.
- Az **éles LAB-mód kapcsoló OFF** marad;
  az új csempe nem teszi azt elérhetővé.
- Nincs új router portforward, DDNS, ingress
  vagy TLS Secret változás. A már létező
  `https://pmqxyz.hopto.org/pandemic/`
  útvonalat használjuk.

## Függőség és üzembe helyezési sorrend

A Pandemic NUC-on futó konténerképe
korábbi lehet a LAB XXX. tesztelt `main`
verziónál. **A landing csempe megjelenése
önmagában nem frissíti a Pandemicet**.
A két repo frissítését külön és sorrendben
végezzük, csak az NUC tesztkapuk és a
GitHub PR-ek merge után.

### 1. Read-only preflight (nincs klasztermódosítás)

```bash
cd ~/codes/pandemic
git switch main
git pull --ff-only
test -z "$(git status --porcelain)"
sudo k3s kubectl get deployment pandemic -n default \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
sudo k3s kubectl get ingress pandemic-game-ingress -n default
curl -fsS https://pmqxyz.hopto.org/pandemic/api/healthz
```

A futó deploymentben **nincs**
`PANDEMIC_LAB_*` környezeti változó vagy
privát Secret mount; a
`scripts/deploy-nuc.sh --apply` ezeket
eleve letiltja, hogy ne írjon felül
meglévő aktivált LAB-konfigurációt.

### 2. Pandemic QA (még deploy előtt)

A Pandemic repo új ágán:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests \
  -p 'test_lab_mobile_ui.py' -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
```

Az összes korábbi 537 teszten felül
**1 új statikus teszt**, tehát **538/538**
várt PASS. Ezután Playwright:

```bash
VENV="$HOME/.local/share/pandemic-lab-browser-venv"
PYTHONPATH=src "$VENV/bin/python" scripts/lab_browser_smoke.py
```

Az új böngészős lépés egy már elmentett
játékoshely mellett `/#lab-preview`
URL-t nyit meg; ellenőrzi, hogy a LAB
létrehozó felület látható marad, a mentett
normál seat-token nem törlődik. **A
Playwright-teszt PASS nélkül nem merge-elhető
a Pandemic PR.**

### 3. Landing QA

```bash
cd ~/codes/landing
python3 -m unittest discover -s tests -v
KUBECTL='sudo k3s kubectl' ./update.sh --target nuc --dry-run
```

A landing saját tesztje ellenőrzi az
azonos domainen maradó HTTPS relatív
hivatkozásokat és azt, hogy a csempe nem
hivatkozik `127.0.0.1:8768` helyi portra.

### 4. Külön jóváhagyott éles frissítési lépések

**Csak a QA és a PR merge után**, amikor a
normál játékosok rövid megszakítása
elfogadható:

1. **Pandemic előbb**: `cd ~/codes/pandemic`,
   `git switch main && git pull --ff-only`;
   az elfogadott merge commit pontos SHA-ját
   ellenőrizni kell. Ezután
   `bash scripts/deploy-nuc.sh --apply`.
   A script csak a `pandemic` Deploymentet
   és Service-t változtatja, a meglévő
   Redis-szobák megmaradnak, de az
   átmeneti memóriabeli LAB-próbaszobák
   **elvesznek**. Ellenőrzés:
   `sudo k3s kubectl rollout status deployment/pandemic -n default`,
   majd `curl -fsS https://pmqxyz.hopto.org/pandemic/api/healthz`.
2. **Landing másodszor**: `cd ~/codes/landing`,
   `git switch main && git pull --ff-only`;
   a tesztelt merge SHA ellenőrzése után
   `KUBECTL='sudo k3s kubectl' ./update.sh --target nuc`.
   Ez a landing ConfigMap és pod frissítése,
   rövid `Recreate` kieséssel.
3. A LAN-tól független eszközön nyisd meg
   `https://pmqxyz.hopto.org/`, majd
   `🧪 Pandemic – LAB próba`. Személyes
   meghívóval bejelentkezett böngészőn
   megjelenik a kétjátékos LAB
   tanulópálya. Külön eszközre
   **külön** meghívós bejelentkezés
   szükséges.

**Ne** indítsd el a gyári deploymentet a
LAB-privát Secret vagy a K3s titkosítás
módosításával; az most külön mérföldkő.

## Korlátok

A Playwright-teszt valódi Chromium,
de mobilméretet **emulál**. Fizikai
Android/iOS böngészőn a távoli,
meghívóval védett használatot külön
kell ellenőrizni. A localhost-only
tesztszervert nem tesszük ki a WAN-ra;
ugyanazt a szintetikus LAB-próba
funkciót használjuk a hivatalos
Pandemic k3s-podon belül.
