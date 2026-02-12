FROM hashicorp/vault:1.15

# Copy config and entrypoint
COPY config.hcl /vault/config/config.hcl
COPY entrypoint.sh /vault/entrypoint.sh
RUN chmod +x /vault/entrypoint.sh

# Data directory — attach a Railway persistent volume at /vault/data
RUN mkdir -p /vault/data

EXPOSE 8200

ENTRYPOINT ["/vault/entrypoint.sh"]
