# GovAI Core — official runtime image (aigov_audit ledger HTTP service).
# Build: docker build -t govai-core:local .
# Run:   docker run --rm -p 8088:8088 -v govai-ledger:/var/lib/govai/ledger ...

FROM rust:1-bookworm AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/src ./src
COPY rust/migrations ./migrations
COPY rust/policy.json rust/policy.dev.json rust/policy.staging.json rust/policy.prod.json ./

RUN cargo build --locked --release --bin aigov_audit

FROM debian:bookworm-slim AS runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libpq5 \
    curl \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --system --gid 1000 govai \
  && useradd --system --uid 1000 --gid govai --home-dir /var/lib/govai --shell /usr/sbin/nologin govai \
  && mkdir -p /app/policies /var/lib/govai/ledger \
  && chown -R govai:govai /app /var/lib/govai

WORKDIR /app

COPY --from=builder --chown=govai:govai /build/target/release/aigov_audit /app/aigov_audit
COPY --from=builder --chown=govai:govai /build/policy.json /build/policy.dev.json /build/policy.staging.json /build/policy.prod.json /app/policies/

# Runtime configuration (set at deploy time): DATABASE_URL, GOVAI_API_KEYS, GOVAI_API_KEYS_JSON
ENV AIGOV_BIND=0.0.0.0:8088 \
    AIGOV_POLICY_DIR=/app/policies \
    AIGOV_ENVIRONMENT=prod \
    GOVAI_LEDGER_DIR=/var/lib/govai/ledger \
    GOVAI_AUTO_MIGRATE=false

EXPOSE 8088

USER govai

ENTRYPOINT ["/app/aigov_audit"]
