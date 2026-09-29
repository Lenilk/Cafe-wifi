FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/cafe-wifi/app:/srv/cafe-wifi

WORKDIR /srv/cafe-wifi

RUN apt-get update \
    && apt-get install --no-install-recommends -y mariadb-client gzip \
    && if ! command -v mysqldump >/dev/null 2>&1; then \
         ln -s "$(command -v mariadb-dump)" /usr/local/bin/mysqldump; \
       fi \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/
COPY tools/ tools/

FROM runtime AS test
RUN pip install --no-cache-dir pytest==8.3.5
COPY tests/ tests/
COPY sql/ sql/
