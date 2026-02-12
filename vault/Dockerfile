FROM hashicorp/vault:1.15

# Copy config and entrypoint
COPY config.hcl /vault/config/config.hcl
COPY entrypoint.sh /vault/entrypoint.sh
RUN chmod +x /vault/entrypoint.sh

# Data directory — mount a Railway persistent volume here
VOLUME /vault/data

EXPOSE 8200

ENTRYPOINT ["/vault/entrypoint.sh"]
