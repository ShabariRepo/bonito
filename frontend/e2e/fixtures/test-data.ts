export const TEST_AWS_CREDENTIALS = {
  access_key_id: "AKIAIOSFODNN7EXAMPLE",
  secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  region: "us-east-1",
};

export const TEST_AZURE_CREDENTIALS = {
  tenant_id: "12345678-1234-1234-1234-123456789012",
  client_id: "12345678-1234-1234-1234-123456789013",
  client_secret: "super-secret-value-here",
  subscription_id: "12345678-1234-1234-1234-123456789014",
};

export const TEST_GCP_CREDENTIALS = {
  project_id: "my-bonito-project",
  service_account_json: '{"type":"service_account","project_id":"my-bonito-project"}',
};

export const EXPECTED_MODEL_COUNTS = {
  aws: 12,
  azure: 8,
  gcp: 7,
};

export const NAV_ITEMS = [
  { name: "Dashboard", href: "/dashboard" },
  { name: "Models", href: "/models" },
  { name: "Deployments", href: "/deployments" },
  { name: "Providers", href: "/providers" },
  { name: "Settings", href: "/settings" },
];

export const API_URL = process.env.API_URL || "http://localhost:8000";
