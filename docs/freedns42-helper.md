# FreeDNS::42 Helper

Lokalny helper CLI do panelu `https://freedns.42.pl`.

Założenia:
- logowanie przez HTML form
- sesja przez `idsession` w URL
- eksport aktualnej strefy do JSON
- plan zmian względem pliku JSON
- zapis tylko przy `apply --write`
- opcjonalny tryb `dyndns-a` dla pojedynczego rekordu `A` przez XML-RPC
- gotowe operacje `TXT` pod wildcard `DNS-01`

## Plik

- [freedns42_zone_helper.py](/root/MikroTik-Mass-Updater/tools/freedns42_zone_helper.py)

## Użycie

```bash
export FREEDNS42_USER='fork'
export FREEDNS42_PASSWORD='...'
```

Eksport:

```bash
python3 tools/freedns42_zone_helper.py export --zone efork.pl --out /tmp/efork.json
```

Plan:

```bash
python3 tools/freedns42_zone_helper.py plan --zone efork.pl --file /tmp/efork.json
```

Zapis:

```bash
python3 tools/freedns42_zone_helper.py apply --zone efork.pl --file /tmp/efork.json --write
```

Pojedynczy rekord `A` przez XML-RPC, bez zapisu:

```bash
python3 tools/freedns42_zone_helper.py dyndns-a --zone efork.pl --record-name home --new-address 192.0.2.10
```

Pojedynczy rekord `A` przez XML-RPC, z zapisem:

```bash
python3 tools/freedns42_zone_helper.py dyndns-a --zone efork.pl --record-name home --new-address 192.0.2.10 --write
```

TXT set, bez zapisu:

```bash
python3 tools/freedns42_zone_helper.py txt-set --zone efork.pl --record-name _acme-challenge.efork.pl --text token
```

TXT delete, bez zapisu:

```bash
python3 tools/freedns42_zone_helper.py txt-delete --zone efork.pl --record-name _acme-challenge.efork.pl --text token
```

Hook ACME:

```bash
export FREEDNS42_USER='fork'
export FREEDNS42_PASSWORD='...'
export FREEDNS42_ZONE='efork.pl'
export FREEDNS42_PROPAGATION_SECONDS='600'

./tools/freedns42_acme_hook.sh present '*.efork.pl' 'token'
./tools/freedns42_acme_hook.sh cleanup '*.efork.pl' 'token'
```

Model użycia:
- `present` dodaje `_acme-challenge`
- aktywnie sprawdza autorytatywny DNS `42.pl` i potem publiczne resolvery
- domyślnie czeka do `900s` na autorytatywny DNS i do `300s` na resolvery publiczne
- `cleanup` usuwa dokładnie ten sam token po walidacji

Do certyfikatu wildcard:
- klient ACME musi używać `DNS-01`
- hook ma sens np. dla `certbot --manual-auth-hook/--manual-cleanup-hook`
- albo jako własny wrapper pod `acme.sh`

Wrapper `certbot + import do NPM`:

```bash
export FREEDNS42_USER='fork'
export FREEDNS42_PASSWORD='...'
export FREEDNS42_ZONE='efork.pl'
export FREEDNS42_PROPAGATION_SECONDS='600'

export NPM_IDENTITY='admin@efork.pl'
export NPM_SECRET='Kolo12wd_'

# bez przypinania do aktywnego hosta, np. staging
CERTBOT_STAGING=1 ASSIGN_TO_PROXY=0 ./tools/issue_wildcard_efork_cert.sh

# produkcja i podpięcie do hosta proxy id=1
CERTBOT_STAGING=0 ASSIGN_TO_PROXY=1 ./tools/issue_wildcard_efork_cert.sh
```

Skrypty:
- [freedns42_certbot_hook.sh](/root/MikroTik-Mass-Updater/tools/freedns42_certbot_hook.sh)
- [npm_certificate_import.py](/root/MikroTik-Mass-Updater/tools/npm_certificate_import.py)
- [issue_wildcard_efork_cert.sh](/root/MikroTik-Mass-Updater/tools/issue_wildcard_efork_cert.sh)

## Ograniczenia

- helper działa przez stary formularz WWW, nie przez oficjalne API
- zapis idzie batchami, bo panel ma po 4 sloty dodawania rekordów na typ
- bez `--write` helper nic nie zmienia
- `dyndns-a` obsługuje tylko pojedynczy rekord `A`
- `txt-set` i `txt-delete` działają przez pełne pobranie strefy i bezpieczny `apply`
- na dziś obsługuje eksport/plan/apply dla:
  - `NS`
  - `MX`
  - `A`
  - `CNAME`
  - `TXT`
  - `WWW redirect/frame`
