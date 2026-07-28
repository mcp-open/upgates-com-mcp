# upgates-mcp platformová varianta — port produktového upgates-com-mcp (TS) na
# openmcp_sdk. Build context připraví platform/deploy/Makefile
# (target build-connector-upgates): tar zabalí upgates-com-mcp + openmcp-sdk
# z repos/konektory a přejmenuje je na `upgates/` + `sdk/`.
FROM python:3.13-alpine@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0

WORKDIR /app

# sdk najprv (upgates-mcp naň závisí v pyproject.toml).
COPY sdk ./sdk
COPY upgates ./upgates
RUN pip install --no-cache-dir --no-compile --only-binary=:all: \
      --require-hashes -r ./upgates/release/runtime-requirements.lock \
    && pip install --no-cache-dir --no-compile --no-deps --no-build-isolation \
      ./sdk ./upgates \
    && pip check

# Non-root běh s pevným UID bez domovského adresáře a login shellu.
RUN addgroup -S -g 10001 openmcp \
    && adduser -S -D -H -u 10001 -G openmcp -s /sbin/nologin openmcp
USER 10001

# `python -m connector` volá run_connector("connector.yaml", mcp) s relatívnou
# cestou k manifestu — WORKDIR preto musí byť priečinok, ktorý connector.yaml
# obsahuje (balík `connector` je nainštalovaný cez pip, teda importovateľný
# nezávisle od cwd).
WORKDIR /app/upgates

EXPOSE 8000

ENTRYPOINT ["python", "-m", "connector"]
