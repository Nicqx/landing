# Játékszoba – közös, hordozható kezdőlap

A hat játék relatív `/sumplete/`, `/tic-tac-toe/`, `/chess/`, `/sudoku/`, `/maffia/`, `/bakos/` útvonalakon érhető el. Nincs a kódban LAN IP vagy külön alkalmazásport; HTTPS-ről nyitva a játékok is HTTPS-en nyílnak meg. A Sumplete, amőba és sakk ötjegyű szobakódja a meglévő szerveroldali útvonalra visz.

A `landing-page-service` továbbra is belső ClusterIP és **80-as service-port**. A digesttel rögzített, ARM64/AMD64-képes nginx nem rootként, a konténerben **8080**-on fut. A fájlrendszer írásvédett, csak `/tmp` írható. Van readiness/liveness ellenőrzés, Content Security Policy és külső fájlba helyezett JavaScript/CSS. Nincs külső CDN vagy buildlépés.

## Közös használat

A parancsokat a repo könyvtárából futtasd. Előfeltétel: Bash, Git, Python 3.9+ és a helyi clusterhez hozzáférő `kubectl` (az ingresshez OpenSSL is kell). Python-csomag telepítése nem szükséges.

```bash
git pull --ff-only
./update.sh --target pi5 --dry-run
./update.sh --target pi5
```

A NUC-on `--target nuc` kell. A parancs ellenőrzi a node nevét és architektúráját; többnode-os clusterhez szándékosan nincs automatikus telepítés. Más kube-context: `--context NEV`. Ha a kubeconfig csak sudo-val olvasható, a teljes script helyett csak a kubectl kapjon jogosultságot:

```bash
KUBECTL='sudo k3s kubectl' ./update.sh --target nuc
```

Az update tiszta munkakönyvtárban `git pull --ff-only` után dolgozik. A `--dry-run` a jelenlegi helyi kódot ellenőrzi a Kubernetes API-val, nem pullol és nem ír a clusterbe. A tudatosan helyi kódhoz `--no-pull` használható. Nincs `reset --hard`, force push, prune vagy tömeges erőforrás-törlés.

Diagnosztika és kapcsolat nélküli manifest-előnézet:

```bash
./scripts/diagnose.sh --target pi5
python3 scripts/manage.py render --target nuc
```

A módosítás előtt a korábbi manifestek `0600` jogosultságú mentése készül a `~/.local/state/nicqx-infra/<target>/<repo>/` könyvtárba. A parancs kiírja a pontos fájlnevet. Más mentési gyökér: `NICQX_STATE_DIR`. A négy repo ugyanazon felhasználó/gép/cél műveleteit helyi zárral sorosítja; több operátor között külön egyeztetés szükséges.

Manifest-visszaállítás a **kiírt mentési fájl** teljes elérési útjával:

```bash
python3 scripts/manage.py rollback --target pi5 --file /teljes/ut/manifest-mentes.json --dry-run
python3 scripts/manage.py rollback --target pi5 --file /teljes/ut/manifest-mentes.json
```

Ez csak ugyanabban a clusterben, a repo engedélyezett erőforrásaira működik. Nem állít vissza adatbázist, és nem törli az időközben létrehozott erőforrásokat. Sikertelen rolloutnál az update hibával áll le; a visszaállítás külön, látható művelet.

Az `availability-calendar`, `availability-calendar-service`, `connectivity-check`, `munkaido`, `munkaido-nyilvantarto`, `rsvp1984`, `rsvp1985` neveket a közös eszköz védi. Más, ismeretlen erőforrásokat sem alkalmaz a repo saját engedélylistáján kívül. Dockerhez, K3s szolgáltatáshoz vagy routerhez egyik update sem nyúl.

## Módosítás

A tartalom: `site/index.html`, `site/style.css`, `site/app.js`. A kiszolgálás: `nginx.conf`. A ConfigMap tartalmának hash-e automatikus podcserét vált ki. A korábbi `landing-page.yaml` helyét a `k8s/resources.json` és az update vette át.

A Deployment neve/selectorja változatlan; egy szándékosan 0-ra állított deployment nem indul el magától. A `Recreate` stratégia miatt a frissítés rövid kieséssel járhat. Az update megvárja a readiness sikerét, hiba esetén kilép.

A kezdőlap nem bizonyítja, hogy minden játék backendje készen áll. A NUC-on jelenleg több játék még nem Ready; a routert emiatt még ne állítsd át. Az útvonalakat az [ingress repo](https://github.com/Nicqx/ingress) kezeli.

Teszt: `python3 -m unittest discover -s tests -v`. A GitHub CI a tényleges, rögzített nginx image-et is indítja a nem-root/írásvédett beállításokkal, és ellenőrzi az egészségvégpontot, asseteket, HTTP fejléceket. Helyben Dockerrel: `python3 scripts/check_nginx.py`.

## Migráció, leállítás és eltávolítás

A kezdőlap állapotmentes: nincs PVC vagy adatbázis. Új gépen klónozd a repót, futtasd a `--target nuc --dry-run`, majd az update parancsot. Az ingress külön repóból települ.

```bash
# ideiglenes leállítás / visszaindítás
sudo k3s kubectl scale deployment/landing-page-deployment -n default --replicas=0
sudo k3s kubectl scale deployment/landing-page-deployment -n default --replicas=1

# eltávolítás; ingresshez és más alkalmazáshoz nem nyúl
sudo k3s kubectl delete deployment/landing-page-deployment service/landing-page-service -n default
```

Rollbackhoz használd az update által kiírt manifestmentést a `scripts/manage.py rollback` paranccsal. A törlés után ugyanaz az `update.sh --target nuc` telepíti újra.
