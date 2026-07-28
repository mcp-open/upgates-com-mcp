# Bezpečnostní politika

Nálezy **neposílejte do veřejných issue**. Pošlete je na
**security@openmcp.cz** s popisem dopadu a kroky k reprodukci. Do hlášení
nevkládejte API klíče ani zákaznická data — ani pseudonymizované tokeny
nejsou náhrada za rozvahu.

Podporovány jsou poslední dvě minor verze konektoru.

## Co nás zajímá nejvíc

- osobní údaj zákazníka e-shopu, který projde do modelu bez pseudonymizace —
  typicky pole, které chybí v `src/connector/pii_fields.py`;
- obejití read-only filtru: konektor nemá jediný zapisující nástroj a nesmí ho
  získat ani nedopatřením;
- volání mimo `egress` allowlist, zvlášť pokus poslat API klíč na jiný host
  než ověřenou instanci Upgates;
- cokoli, co dostane API klíč nebo tělo upstream odpovědi do chybové zprávy
  pro model nebo do logu;
- vstup od modelu, který se dostane do URL nesestavené z ověřených segmentů.

## Co bezpečnostní chyba není

- **Model se dá přemluvit textem z e-shopu** (názvem produktu, poznámkou
  v objednávce). To je vlastnost LLM. Konektor ji neřeší, jen ohraničuje
  dopad — u čtecího konektoru zůstává u toho, co si model přečte.
- **Chybějící `OPENMCP_PII_SALT` shodí start.** To je záměr: tichý fallback na
  náhodný salt by rozbil stabilitu tokenů až po prvním restartu.
- Neplatné přihlašovací údaje vrací `credential_invalid` a konektor nefunguje.
  To je správné chování, ne výpadek.
