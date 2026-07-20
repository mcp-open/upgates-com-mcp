"""GDPR pseudonymizace odpovědí Upgates API.

Cíl: do LLM nesmí protéct surová osobní data zákazníků (e-maily, telefony,
jména, adresy, IČO/DIČ, bankovní spojení). Každá citlivá hodnota se nahradí
stabilním tokenem typu ``<EMAIL_3f9c1a2b4d5e>``. LLM tak umí o záznamu uvažovat
a odkazovat na něj, ale reálnou hodnotu nevidí.

Port anonymizace z `upgates-client.ts` (`anonymizeData`) + `handlers/tools.ts`
(kde se volala nad orders/invoices/customers/carts/owner). Přenáší se **stejná
sada polí** jako v TS (explicitní seznam + substring vzory name/email/phone/
address/street/city/zip), ale místo nereverzibilního maskování (`***ANONYMIZED***`)
se hodnota nahradí **HMAC-odvozeným tokenem** — přesně jako v raynet-mcp
(`connector.pii`). Důvody:

* **Stabilita bez stavu.** Stejná hodnota dá stejný token v každém procesu
  i podu, bez čehokoli na disku. Maskování `***ANONYMIZED***` naopak slepilo
  všechny hodnoty do jedné — LLM nerozliší dva zákazníky.
* **Žádný re-identifikační klíč.** Token zpět rozklíčovat nelze; nevzniká
  žádná mapa token→hodnota (ta by byla sama o sobě PII aktivum).
* **Izolace tenantů.** Klíč je odvozený ze ``sub``, takže stejný e-mail dá
  u dvou e-shopů jiný token a tokeny nejdou korelovat napříč tenanty.

Token::

    token = "<" + KATEGORIE + "_" + HMAC-SHA256(klíč, kategorie + ":" + hodnota)[:12] + ">"
    klíč  = HMAC-SHA256(OPENMCP_PII_SALT, sub)

Rozdíly oproti věrnému TS portu (záměrné, dokumentované):

* **Volnotextové poznámky** (``customer_note``, ``internal_note``, ``note``) se
  jen scrubnou regexem (e-maily/telefony/URL uvnitř → tokeny, zbytek textu
  zůstane) místo úplného zahození — obchodní kontext poznámky je užitečný a
  není sám o sobě PII. Stejný přístup jako raynet FREETEXT_FIELDS.
* **Katalogové ``code``** (kód produktu/dopravy/platby) se NEtokenizuje —
  jsou to identifikátory katalogu, ne osobní data, a LLM je potřebuje na
  odkazování produktů v objednávce. ``customer_code`` (identifikátor zákazníka)
  se tokenizuje dál.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any

# Délka hex části tokenu (48 bitů). Viz rozvaha o kolizích v raynet pii.py.
TOKEN_HEX_LEN = 12
TOKEN_RE = re.compile(rf"<[A-Z]+_[0-9a-f]{{{TOKEN_HEX_LEN}}}>")

# Proměnná se salt-em, ze kterého se odvozují per-tenant klíče. Bez ní konektor
# odmítne pracovat — tichý fallback na náhodný salt by stabilitu tokenů zrušil
# a projevilo by se to až po prvním restartu podu.
SALT_ENV = "OPENMCP_PII_SALT"

# --- Názvy koncových polí → kategorie tokenu (case-insensitive) ---------------
# Portováno z `sensitiveFields` v upgates-client.ts. Skalární pole, která
# tokenizujeme přímo podle názvu.
FIELD_CATEGORY: dict[str, str] = {
    # e-mail
    "email": "EMAIL",
    "customer_email": "EMAIL",
    "vendoremail": "EMAIL",
    # telefon
    "phone": "PHONE",
    "phonenumber": "PHONE",
    "phone_number": "PHONE",
    "fax": "PHONE",
    # jména osob
    "firstname": "NAME",
    "surname": "NAME",
    "firstname_invoice": "NAME",
    "surname_invoice": "NAME",
    "firstname_postal": "NAME",
    "surname_postal": "NAME",
    "customer_name": "NAME",
    "name": "NAME",
    "nickname": "NAME",
    "degree": "NAME",
    "salutation": "NAME",
    "declension": "NAME",
    # firma
    "company": "COMPANY",
    "company_name": "COMPANY",
    "company_postal": "COMPANY",
    # adresa
    "street": "ADDR",
    "street_invoice": "ADDR",
    "street_postal": "ADDR",
    "city": "ADDR",
    "city_invoice": "ADDR",
    "city_postal": "ADDR",
    "state": "ADDR",
    "state_invoice": "ADDR",
    "state_postal": "ADDR",
    "zip": "ADDR",
    "zip_invoice": "ADDR",
    "zip_postal": "ADDR",
    "zip_code": "ADDR",
    "address": "ADDR",
    # firemní identifikátory
    "ico": "REGNUM",
    "company_number": "REGNUM",
    "dic": "TAXNUM",
    "vat_number": "TAXNUM",
    # identifikátor zákazníka
    "customer_code": "CUSTCODE",
    # ostatní kontakt
    "im": "CONTACT",
    # bankovní spojení
    "bank_account": "BANK",
    "account_number": "BANK",
    "iban": "BANK",
    "swift": "BANK",
    "specific_symbol": "BANK",
    "variable_symbol": "BANK",
}

# Volnotextová pole — jen scrub vnořených e-mailů/telefonů/URL, zbytek ponech.
FREETEXT_FIELDS = {"customer_note", "internal_note", "note"}

# Substringové vzory z `anonymizeByPattern` v upgates-client.ts. Fail-closed
# fallback pro nevyjmenovaná pole (custom fields, *_invoice/*_postal varianty).
_PATTERN_CATEGORY: tuple[tuple[str, str], ...] = (
    ("email", "EMAIL"),
    ("phone", "PHONE"),
    ("street", "ADDR"),
    ("address", "ADDR"),
    ("city", "ADDR"),
    ("zip", "ADDR"),
    ("name", "NAME"),
)

# --- Regex fallback (zachytí PII i ve volném textu / custom fields) ------------
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RE_PHONE = re.compile(r"(?<![\w.])(?:\+?\d[\d\s()\-]{7,}\d)(?![\w])")
RE_URL = re.compile(r"https?://[^\s\"'<>]+")
# Ochrana před falešnou shodou data/času jako telefonu (např. "2022-06-18 13").
RE_DATELIKE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")


def require_salt() -> str:
    """Vrať salt, nebo vysvětli, proč konektor nemůže běžet.

    Volá se při startu (`__main__`) i před každým odvozením klíče. Tichý
    fallback na náhodný per-process salt by stabilitu tokenů zrušil.
    """
    salt = os.environ.get(SALT_ENV, "").strip()
    if not salt:
        raise RuntimeError(
            f"Chybí {SALT_ENV}. Bez něj by tokeny nebyly stabilní napříč restarty "
            f"a pseudonymizace by tiše ztratila smysl."
        )
    return salt


def derive_key(sub: str) -> bytes:
    """Odvoď per-tenant HMAC klíč ze ``sub`` a operátorského saltu.

    Salt patří do k8s secretu, nikdy do manifestu ani image. Jeho únik by
    umožnil re-identifikaci hrubou silou (e-maily mají nízkou entropii).
    """
    salt = require_salt()
    return hmac.new(salt.encode("utf-8"), sub.encode("utf-8"), hashlib.sha256).digest()


def _pattern_category(lkey: str) -> str | None:
    """Kategorie podle substringu v názvu pole (port `anonymizeByPattern`)."""
    for needle, category in _PATTERN_CATEGORY:
        if needle in lkey:
            return category
    return None


class Pseudonymizer:
    """Nahrazuje PII tokeny odvozenými HMAC-em z hodnoty.

    Instance je určená pro **jeden request** (klíč je per-tenant). Nedrží žádný
    stav, takže nepotřebuje zámek — ``sanitize`` běží v jednom vlákně nad jednou
    odpovědí.
    """

    def __init__(self, key: bytes) -> None:
        self._key = key

    def _token_for(self, category: str, value: Any) -> str:
        norm = str(value)
        digest = hmac.new(
            self._key, f"{category}:{norm}".encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"<{category}_{digest[:TOKEN_HEX_LEN]}>"

    def _sub_phone(self, m: re.Match) -> str:
        """Tokenizuj jen pokud shoda opravdu vypadá jako telefon (ne datum/čas)."""
        raw = m.group(0)
        if RE_DATELIKE.search(raw):
            return raw
        if sum(c.isdigit() for c in raw) < 9:
            return raw
        return self._token_for("PHONE", raw)

    def _scrub_text(self, text: str) -> str:
        """Scrub volnotextového pole: e-maily, URL i telefony."""
        text = RE_EMAIL.sub(lambda m: self._token_for("EMAIL", m.group(0)), text)
        text = RE_URL.sub(lambda m: self._token_for("URL", m.group(0)), text)
        text = RE_PHONE.sub(self._sub_phone, text)
        return text

    def sanitize(self, data: Any) -> Any:
        return self._walk(data)

    def _walk(self, node: Any) -> Any:
        if isinstance(node, dict):
            return {k: self._handle_field(k, v) for k, v in node.items()}
        if isinstance(node, list):
            return [self._walk(item) for item in node]
        if isinstance(node, str):
            # Fail-closed: i u nevyjmenovaných polí scrubujeme e-maily/URL/telefony.
            return self._scrub_text(node)
        return node

    def _handle_field(self, key: str, value: Any) -> Any:
        lkey = key.lower()

        # 1) Volnotextová pole — regex scrub, zbytek ponech.
        if lkey in FREETEXT_FIELDS and isinstance(value, str):
            return self._scrub_text(value)

        # 2) Skalární PII pole podle názvu (nebo substringu jako fallback).
        category = FIELD_CATEGORY.get(lkey) or _pattern_category(lkey)
        if category is not None:
            if isinstance(value, bool) or value is None or value == "":
                return value
            if isinstance(value, (str, int, float)):
                return self._token_for(category, value)
            if isinstance(value, list):
                return [
                    self._token_for(category, v)
                    if isinstance(v, (str, int, float)) and not isinstance(v, bool)
                    and v not in (None, "")
                    else self._walk(v)
                    for v in value
                ]
            return self._walk(value)

        # 3) Jinak rekurze (zachytí vnořené adresy, customer objekt, custom fields…).
        return self._walk(value)
