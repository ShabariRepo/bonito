# Vault Production Hardening Guide

> **Status:** Documentation only — do not apply these changes until a dedicated deployment task is planned.

This document describes what needs to change to move HashiCorp Vault out of **dev mode** (current state) into a production-ready configuration for Bonito.

---

## Current State (Dev Mode)

- Vault runs in dev mode via Docker Compose (`docker-compose.yml`)
- Uses a hardcoded dev token: `bonito-dev-token`
- All data is **in-memory** — lost on restart
- No TLS, no audit logging, no access policies
- Single instance, no HA

This is fine for local development but **must not** be used in staging or production.

---

## 1. Switch from Dev Mode to Production Mode

### Storage Backend

Replace in-memory storage with a persistent backend. Two recommended options:

#### Option A: File Backend (Simple, Single-Node)

Already partially configured in `vault/config-prod.hcl`:

```hcl
storage "file" {
  path = "/vault/data"
}
```

- **Pros:** Simple, no external dependencies
- **Cons:** Single-node only, no HA
- **Use for:** Small deployments, staging environments
- **Important:** Mount `/vault/data` as a persistent volume (Docker volume or EBS/PD)

#### Option B: Consul Backend (HA, Multi-Node)

```hcl
storage "consul" {
  address = "consul:8500"
  path    = "vault/"
  scheme  = "http"  # use "https" if Consul has TLS
}
```

- **Pros:** HA with automatic leader election, proven at scale
- **Cons:** Requires running a Consul cluster (3+ nodes)
- **Use for:** Production deployments needing high availability

#### Option C: Integrated Raft Storage (HA, No External Deps)

```hcl
storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}
```

- **Pros:** Built-in HA without external dependencies (Vault 1.4+)
- **Cons:** Requires careful cluster bootstrapping
- **Use for:** Production deployments where running Consul is overkill

### Remove Dev Mode Flag

Ensure the Vault container command does **not** include `server -dev`. Use:

```yaml
command: ["server", "-config=/vault/config/config.hcl"]
```

---

## 2. Auto-Unseal

In production mode, Vault starts **sealed** after every restart. Manual unsealing is impractical. Configure auto-unseal with a cloud KMS.

### AWS KMS (Recommended for AWS/Railway deployments)

```hcl
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "arn:aws:kms:us-east-1:ACCOUNT:key/KEY-ID"
  # Credentials from IAM role or env vars:
  # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
}
```

- Create a dedicated KMS key with minimal permissions (`kms:Encrypt`, `kms:Decrypt`, `kms:DescribeKey`)
- Use IAM roles (not static keys) when possible
- Enable KMS key rotation

### Azure Key Vault

```hcl
seal "azurekeyvault" {
  tenant_id  = "TENANT-ID"
  vault_name = "bonito-vault-unseal"
  key_name   = "vault-unseal-key"
  # Authenticate via managed identity or env vars:
  # AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
}
```

### GCP Cloud KMS

```hcl
seal "gcpckms" {
  project    = "bonito-prod"
  region     = "us-central1"
  key_ring   = "vault-keyring"
  crypto_key = "vault-unseal"
}
```

---

## 3. Audit Logging

Enable audit logging to capture **every** Vault operation. Critical for compliance.

### File Audit Backend

```bash
vault audit enable file file_path=/vault/logs/audit.log
```

- Rotate logs with logrotate or ship to a log aggregator
- Each entry is a JSON line (request + response)
- **HMAC-hashed by default** — sensitive values are not logged in plaintext

### Syslog Backend (Alternative)

```bash
vault audit enable syslog tag="vault" facility="AUTH"
```

### Best Practices

- Enable **at least two** audit backends (if one blocks, Vault stops responding — by design)
- Ship audit logs to an immutable store (S3 with Object Lock, CloudWatch, etc.)
- Monitor for: root token usage, policy changes, auth mount changes, secret access to sensitive paths

---

## 4. Access Policies (Replace Root Token)

The current setup uses a root token everywhere. In production:

### Create an AppRole for the Bonito Backend

```bash
# Enable AppRole auth
vault auth enable approle

# Create a policy for the Bonito backend
vault policy write bonito-backend - <<EOF
# Read/write secrets under bonito/
path "bonito/data/*" {
  capabilities = ["create", "update", "read"]
}
path "bonito/metadata/*" {
  capabilities = ["list", "read"]
}
# Deny everything else
path "*" {
  capabilities = ["deny"]
}
EOF

# Create the AppRole
vault write auth/approle/role/bonito-backend \
  token_policies="bonito-backend" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=0 \
  secret_id_num_uses=0
```

### Update the Bonito Backend

Replace `VAULT_TOKEN=bonito-dev-token` with AppRole authentication:

```python
# Authenticate with AppRole, get a short-lived token
resp = httpx.post(f"{VAULT_ADDR}/v1/auth/approle/login", json={
    "role_id": os.getenv("VAULT_ROLE_ID"),
    "secret_id": os.getenv("VAULT_SECRET_ID"),
})
token = resp.json()["auth"]["client_token"]
```

- Tokens are short-lived (1h) and must be renewed
- `VaultClient` should handle token renewal automatically
- Store `VAULT_ROLE_ID` and `VAULT_SECRET_ID` as deployment secrets (Railway env vars, K8s secrets, etc.)

### Revoke the Root Token

Once AppRole is working:

```bash
vault token revoke <root-token>
```

Generate new root tokens only for emergency recovery using `vault operator generate-root`.

---

## 5. TLS Configuration

All Vault traffic must be encrypted in production.

### Option A: TLS Termination at Vault

```hcl
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/tls/cert.pem"
  tls_key_file  = "/vault/tls/key.pem"
  # Optional: require client cert (mTLS)
  # tls_require_and_verify_client_cert = true
  # tls_client_ca_file = "/vault/tls/ca.pem"
}
```

- Use certs from Let's Encrypt, ACM, or an internal CA
- Mount certs as secrets/volumes, never bake into images

### Option B: TLS Termination at Load Balancer / Reverse Proxy

If Vault sits behind a reverse proxy (nginx, Traefik, Railway's internal network):

```hcl
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # OK if traffic is internal-only
}
```

- Ensure the network between the proxy and Vault is private and trusted
- Railway's internal networking qualifies (traffic stays within private network)

### Update Bonito Backend

Set `VAULT_ADDR=https://vault.internal:8200` and, if using a custom CA:

```python
httpx.AsyncClient(verify="/path/to/ca.pem")
```

---

## 6. Backup Strategy

### Raft Snapshots (if using Raft storage)

```bash
# Automated daily snapshot
vault operator raft snapshot save /backups/vault-$(date +%Y%m%d).snap
```

- Upload snapshots to S3/GCS with versioning
- Test restoration periodically

### File Backend Backups

- Snapshot the `/vault/data` directory while Vault is idle or paused
- Or use filesystem-level snapshots (EBS snapshots, ZFS snapshots)

### Consul Backend Backups

```bash
consul snapshot save /backups/consul-$(date +%Y%m%d).snap
```

### Secret Zero Problem

Back up the unseal keys / recovery keys securely:

- Store in a separate, offline location (e.g., printed in a safe, separate KMS)
- Use Shamir's Secret Sharing (Vault's default) — require M of N keys
- Document the recovery procedure and test it annually

---

## 7. Migration Checklist

```
[ ] Choose storage backend (file vs consul vs raft)
[ ] Set up persistent volume for Vault data
[ ] Configure auto-unseal with cloud KMS
[ ] Generate TLS certs (or confirm TLS termination at proxy)
[ ] Create Vault policies for Bonito backend
[ ] Set up AppRole auth
[ ] Update Bonito env vars (VAULT_ROLE_ID, VAULT_SECRET_ID, VAULT_ADDR)
[ ] Update VaultClient to use AppRole token renewal
[ ] Enable 2+ audit backends
[ ] Ship audit logs to immutable storage
[ ] Back up unseal/recovery keys securely
[ ] Test backup + restore procedure
[ ] Revoke root token
[ ] Update docker-compose.prod.yml to use production config
[ ] Load test to verify Vault performance under expected load
[ ] Document runbook for Vault recovery scenarios
```

---

## References

- [Vault Production Hardening Guide](https://developer.hashicorp.com/vault/tutorials/operations/production-hardening)
- [Vault Reference Architecture](https://developer.hashicorp.com/vault/tutorials/day-one-raft/raft-reference-architecture)
- [Auto-Unseal with AWS KMS](https://developer.hashicorp.com/vault/tutorials/auto-unseal/autounseal-aws-kms)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/docs/auth/approle)
- [Audit Devices](https://developer.hashicorp.com/vault/docs/audit)
