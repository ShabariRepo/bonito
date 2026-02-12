storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
  # Railway internal networking handles TLS termination.
  # For external access, Railway's edge proxy adds HTTPS.
}

ui = true

api_addr = "http://0.0.0.0:8200"

# Required for containers (no swap/mlock support)
disable_mlock = true

default_lease_ttl = "768h"
max_lease_ttl    = "8760h"
