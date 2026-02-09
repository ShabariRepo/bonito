FROM hashicorp/vault:1.15

ENV VAULT_DEV_ROOT_TOKEN_ID=bonito-prod-token
ENV VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200

EXPOSE 8200

# Run in dev mode — data is ephemeral but we seed on backend startup
CMD ["vault", "server", "-dev"]
