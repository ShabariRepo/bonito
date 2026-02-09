FROM hashicorp/vault:1.15

# Copy production config
COPY config-prod.hcl /vault/config/vault.hcl
COPY init-prod.sh /vault/init-prod.sh

RUN chmod +x /vault/init-prod.sh

# Vault data directory
RUN mkdir -p /vault/data

EXPOSE 8200

# Start Vault server
CMD ["vault", "server", "-config=/vault/config/vault.hcl"]
