# upgates-mcp platformová varianta — port produktového upgates-com-mcp (TS) na
# openmcp_sdk. Build context připraví platform/deploy/Makefile
# (target build-connector-upgates): tar zabalí upgates-com-mcp + openmcp-sdk
# z repos/konektory a přejmenuje je na `upgates/` + `sdk/`.
FROM python:3.13-slim

WORKDIR /app

# sdk najprv (upgates-mcp naň závisí v pyproject.toml).
COPY sdk ./sdk
COPY upgates ./upgates
RUN pip install --no-cache-dir --no-compile ./sdk ./upgates

# Non-root beh — rovnaké defaulty ako ostatné konektory.
RUN useradd --uid 10001 --system --no-create-home --shell /usr/sbin/nologin openmcp
USER 10001

# `python -m connector` volá run_connector("connector.yaml", mcp) s relatívnou
# cestou k manifestu — WORKDIR preto musí byť priečinok, ktorý connector.yaml
# obsahuje (balík `connector` je nainštalovaný cez pip, teda importovateľný
# nezávisle od cwd).
WORKDIR /app/upgates

EXPOSE 8000

ENTRYPOINT ["python", "-m", "connector"]
