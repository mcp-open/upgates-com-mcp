"""upgates — čtecí přístup k Upgates e-shop API (v2) nad `openmcp_sdk`.

Balík se jmenuje neutrálně `connector` (slug žije výhradně v `connector.yaml`,
ne v názvu balíku). Port produktového `upgates-com-mcp` (TypeScript) na SDK
dual-mode: business logika (client / optimizers / anonymizace) se přenáší
věrně, identita a credentials teď přicházejí z `openmcp_sdk.current_context()`
(žádné UPGATES_API_* env proměnné — to byl standalone režim). Hostovaná
varianta je **jen pro čtení** (write nástroje z TS jsou vynechány).
"""
