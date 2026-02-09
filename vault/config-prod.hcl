storage "file" {
  path = "/vault/data"
}

# TLS listener — use when you have certs (e.g., behind a reverse proxy with TLS termination)
# For Railway internal networking, TLS is not needed (traffic stays within private network).
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
  # To enable TLS, set tls_disable = 0 and uncomment:
  # tls_cert_file = "/vault/tls/cert.pem"
  # tls_key_file  = "/vault/tls/key.pem"
}

ui = true

api_addr = "http://0.0.0.0:8200"

disable_mlock = true

default_lease_ttl = "768h"
max_lease_ttl = "8760h"
