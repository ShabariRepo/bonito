storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/tls/cert.pem"
  tls_key_file  = "/vault/tls/key.pem"
}

ui = false

api_addr = "https://0.0.0.0:8200"

default_lease_ttl = "768h"
max_lease_ttl = "8760h"
