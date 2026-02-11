"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.provider import (
    AWSCredentials,
    AzureCredentials,
    ConnectionStatus,
    GCPCredentials,
    ProviderConnect,
    ProviderType,
)


class TestConnectionStatusEnum:
    def test_all_values(self):
        assert ConnectionStatus.pending == "pending"
        assert ConnectionStatus.active == "active"
        assert ConnectionStatus.error == "error"
        assert ConnectionStatus.disconnected == "disconnected"

    def test_enum_count(self):
        assert len(ConnectionStatus) == 4


class TestProviderType:
    def test_valid_types(self):
        assert ProviderType.aws == "aws"
        assert ProviderType.azure == "azure"
        assert ProviderType.gcp == "gcp"

    def test_enum_count(self):
        assert len(ProviderType) == 5


class TestProviderConnect:
    # Valid credential payloads for each provider type
    _AWS_CREDS = {"access_key_id": "A" * 20, "secret_access_key": "B" * 40, "region": "us-east-1"}
    _GCP_CREDS = {"project_id": "my-project", "service_account_json": '{"type":"sa"}', "region": "us-central1"}

    def test_valid_aws(self):
        pc = ProviderConnect(provider_type="aws", credentials=self._AWS_CREDS)
        assert pc.provider_type == ProviderType.aws

    def test_invalid_provider_type(self):
        with pytest.raises(ValidationError):
            ProviderConnect(provider_type="oracle", credentials={})

    def test_credentials_required(self):
        with pytest.raises(ValidationError):
            ProviderConnect(provider_type="aws")

    def test_name_optional(self):
        pc = ProviderConnect(provider_type="gcp", credentials=self._GCP_CREDS)
        assert pc.name is None

    def test_name_provided(self):
        pc = ProviderConnect(provider_type="gcp", credentials=self._GCP_CREDS, name="My GCP")
        assert pc.name == "My GCP"


class TestAWSCredentials:
    def test_valid(self):
        c = AWSCredentials(access_key_id="A" * 20, secret_access_key="B" * 40)
        assert c.region == "us-east-1"  # default

    def test_access_key_too_short(self):
        with pytest.raises(ValidationError):
            AWSCredentials(access_key_id="short", secret_access_key="B" * 40)

    def test_secret_key_too_short(self):
        with pytest.raises(ValidationError):
            AWSCredentials(access_key_id="A" * 20, secret_access_key="short")

    def test_custom_region(self):
        c = AWSCredentials(access_key_id="A" * 20, secret_access_key="B" * 40, region="eu-west-1")
        assert c.region == "eu-west-1"


class TestAzureCredentials:
    def test_valid(self):
        c = AzureCredentials(
            tenant_id="t", client_id="c", client_secret="s", subscription_id="sub"
        )
        assert c.tenant_id == "t"

    def test_missing_tenant_id(self):
        with pytest.raises(ValidationError):
            AzureCredentials(client_id="c", client_secret="s", subscription_id="sub")

    def test_missing_client_id(self):
        with pytest.raises(ValidationError):
            AzureCredentials(tenant_id="t", client_secret="s", subscription_id="sub")

    def test_missing_client_secret(self):
        with pytest.raises(ValidationError):
            AzureCredentials(tenant_id="t", client_id="c", subscription_id="sub")

    def test_missing_subscription_id(self):
        with pytest.raises(ValidationError):
            AzureCredentials(tenant_id="t", client_id="c", client_secret="s")


class TestGCPCredentials:
    def test_valid(self):
        c = GCPCredentials(project_id="proj", service_account_json='{"type":"sa"}')
        assert c.project_id == "proj"

    def test_missing_project_id(self):
        with pytest.raises(ValidationError):
            GCPCredentials(service_account_json='{"type":"sa"}')

    def test_missing_service_account_json(self):
        with pytest.raises(ValidationError):
            GCPCredentials(project_id="proj")
