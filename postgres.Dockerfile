FROM postgis/postgis:16-3.4

# Build pgvector from source (no apt needed — avoids Docker Desktop proxy issues)
RUN apt-get update -o Acquire::https::Verify-Peer=false \
      -o Acquire::https::Verify-Host=false \
      -o Acquire::AllowInsecureRepositories=true \
    && apt-get install -y --no-install-recommends \
       --allow-unauthenticated \
       build-essential postgresql-server-dev-16 git ca-certificates \
    && git -c http.sslVerify=false clone --depth 1 \
       https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector && make && make install \
    && rm -rf /tmp/pgvector \
    && rm -rf /var/lib/apt/lists/*
