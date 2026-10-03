# CodinX di dalam container (berjalan sebagai root, sesuai syarat CodinX).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/codinx
COPY . /opt/codinx
RUN ln -s /opt/codinx/bin/codinx /usr/local/bin/codinx && chmod +x /opt/codinx/bin/codinx
# Rahasia lewat environment / --env-file, JANGAN di-COPY ke image (.env sudah ada di .dockerignore).
WORKDIR /work
ENTRYPOINT ["codinx"]
