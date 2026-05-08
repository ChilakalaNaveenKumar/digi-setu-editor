# Caddy + caddy-dns/cloudflare baked in.
#
# The stock `caddy` image doesn't include third-party DNS providers,
# but our ACME setup needs DNS-01 (so we can keep 80/443 proxied
# through Cloudflare while still renewing Let's Encrypt certs from
# the VM). xcaddy builds a custom binary with the plugin, then we
# copy it into the slim final stage.

ARG CADDY_VERSION=2.9.1

FROM caddy:${CADDY_VERSION}-builder AS builder
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare

FROM caddy:${CADDY_VERSION}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
