"""
Log Integration Service

Handles forwarding logs to external observability platforms:
- Datadog, Splunk, CloudWatch (Tier 1 - fully implemented)
- Elasticsearch, Azure Monitor, GCP Logging, Webhook, Cloud Storage (Tier 2 - stubbed)
"""

import json
import time
import uuid
import logging
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.vault import vault_client
from app.models.logging import PlatformLog, LogIntegration

logger = logging.getLogger(__name__)


class IntegrationHandler(ABC):
    """Base class for log integration handlers."""
    
    @abstractmethod
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to the external system."""
        pass
    
    @abstractmethod
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test connectivity to the external system."""
        pass
    
    async def get_credentials(self, integration: LogIntegration) -> Dict[str, str]:
        """Retrieve credentials from Vault."""
        try:
            credentials = await vault_client.read_secret(integration.credentials_path)
            return credentials
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for {integration.name}: {e}")
            raise
    
    def format_log_entry(self, log: PlatformLog) -> Dict[str, Any]:
        """Convert PlatformLog to a standard format for external systems."""
        return {
            "id": str(log.id),
            "timestamp": log.created_at.isoformat(),
            "org_id": str(log.org_id),
            "log_type": log.log_type,
            "event_type": log.event_type,
            "severity": log.severity,
            "trace_id": str(log.trace_id) if log.trace_id else None,
            "user_id": str(log.user_id) if log.user_id else None,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "resource_type": log.resource_type,
            "action": log.action,
            "duration_ms": log.duration_ms,
            "cost": log.cost,
            "message": log.message,
            "metadata": log.metadata or {}
        }


# ─── Tier 1 Integrations (Fully Implemented) ───

class DatadogHandler(IntegrationHandler):
    """Handler for Datadog logs integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to Datadog via HTTP API."""
        credentials = await self.get_credentials(integration)
        api_key = credentials.get("api_key")
        
        if not api_key:
            raise ValueError("Datadog API key not found in credentials")
        
        config = integration.config
        site = config.get("site", "datadoghq.com")
        service = config.get("service", "bonito")
        source = config.get("source", "bonito")
        tags = config.get("tags", [])
        
        # Format logs for Datadog
        formatted_logs = []
        for log in logs:
            formatted_log = self.format_log_entry(log)
            formatted_log.update({
                "service": service,
                "source": source,
                "tags": tags + [f"org_id:{log.org_id}", f"log_type:{log.log_type}"],
                "level": self._map_severity_to_datadog(log.severity)
            })
            formatted_logs.append(formatted_log)
        
        # Send to Datadog
        url = f"https://http-intake.logs.{site}/v1/input/{api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=formatted_logs,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status not in [200, 202]:
                    error_text = await response.text()
                    raise Exception(f"Datadog API error {response.status}: {error_text}")
        
        logger.debug(f"Sent {len(logs)} logs to Datadog for {integration.name}")
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test Datadog connection by sending a test log."""
        start_time = time.time()
        
        try:
            credentials = await self.get_credentials(integration)
            api_key = credentials.get("api_key")
            
            if not api_key:
                return {"success": False, "message": "API key not found"}
            
            config = integration.config
            site = config.get("site", "datadoghq.com")
            
            # Send test log
            test_log = {
                "message": "Bonito log integration test",
                "service": config.get("service", "bonito"),
                "source": config.get("source", "bonito"),
                "level": "info",
                "tags": config.get("tags", []) + ["test:true"]
            }
            
            url = f"https://http-intake.logs.{site}/v1/input/{api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=[test_log],
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status in [200, 202]:
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "response_time_ms": response_time_ms
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "message": f"HTTP {response.status}: {error_text}",
                            "response_time_ms": response_time_ms
                        }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def _map_severity_to_datadog(self, severity: str) -> str:
        """Map Bonito severity to Datadog log level."""
        mapping = {
            "debug": "debug",
            "info": "info",
            "warn": "warn",
            "error": "error",
            "critical": "fatal"
        }
        return mapping.get(severity, "info")


class SplunkHandler(IntegrationHandler):
    """Handler for Splunk HEC integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to Splunk via HTTP Event Collector."""
        credentials = await self.get_credentials(integration)
        token = credentials.get("token")
        
        if not token:
            raise ValueError("Splunk HEC token not found in credentials")
        
        config = integration.config
        host = config.get("host")
        port = config.get("port", 8088)
        index = config.get("index", "main")
        source = config.get("source", "bonito")
        sourcetype = config.get("sourcetype", "json")
        
        if not host:
            raise ValueError("Splunk host not configured")
        
        # Format logs for Splunk HEC
        events = []
        for log in logs:
            event_data = self.format_log_entry(log)
            event = {
                "time": int(log.created_at.timestamp()),
                "host": source,
                "source": source,
                "sourcetype": sourcetype,
                "index": index,
                "event": event_data
            }
            events.append(json.dumps(event))
        
        # Send to Splunk HEC
        url = f"https://{host}:{port}/services/collector"
        payload = "\n".join(events)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=payload,
                headers={
                    "Authorization": f"Splunk {token}",
                    "Content-Type": "application/json"
                },
                ssl=False,  # Often needed for self-signed certs
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Splunk HEC error {response.status}: {error_text}")
        
        logger.debug(f"Sent {len(logs)} logs to Splunk for {integration.name}")
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test Splunk HEC connection."""
        start_time = time.time()
        
        try:
            credentials = await self.get_credentials(integration)
            token = credentials.get("token")
            
            if not token:
                return {"success": False, "message": "HEC token not found"}
            
            config = integration.config
            host = config.get("host")
            port = config.get("port", 8088)
            
            if not host:
                return {"success": False, "message": "Splunk host not configured"}
            
            # Send test event
            test_event = {
                "time": int(time.time()),
                "host": "bonito",
                "source": "bonito",
                "sourcetype": "json",
                "event": {"message": "Bonito log integration test", "test": True}
            }
            
            url = f"https://{host}:{port}/services/collector"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=json.dumps(test_event),
                    headers={"Authorization": f"Splunk {token}"},
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "response_time_ms": response_time_ms
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "message": f"HTTP {response.status}: {error_text}",
                            "response_time_ms": response_time_ms
                        }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }


class CloudWatchHandler(IntegrationHandler):
    """Handler for AWS CloudWatch Logs integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to AWS CloudWatch Logs."""
        credentials = await self.get_credentials(integration)
        access_key = credentials.get("access_key_id")
        secret_key = credentials.get("secret_access_key")
        
        if not access_key or not secret_key:
            raise ValueError("AWS credentials not found")
        
        config = integration.config
        region = config.get("region", "us-east-1")
        log_group = config.get("log_group")
        log_stream = config.get("log_stream", f"bonito-{int(time.time())}")
        
        if not log_group:
            raise ValueError("CloudWatch log group not configured")
        
        # Create CloudWatch client
        client = boto3.client(
            'logs',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        try:
            # Ensure log stream exists
            try:
                client.create_log_stream(
                    logGroupName=log_group,
                    logStreamName=log_stream
                )
            except client.exceptions.ResourceAlreadyExistsException:
                pass
            
            # Format log events
            events = []
            for log in logs:
                event_data = self.format_log_entry(log)
                events.append({
                    'timestamp': int(log.created_at.timestamp() * 1000),
                    'message': json.dumps(event_data)
                })
            
            # Sort by timestamp (required by CloudWatch)
            events.sort(key=lambda x: x['timestamp'])
            
            # Send logs in batches (CloudWatch has a 10k event limit)
            batch_size = 10000
            for i in range(0, len(events), batch_size):
                batch = events[i:i + batch_size]
                
                # Get sequence token if needed
                sequence_token = None
                try:
                    response = client.describe_log_streams(
                        logGroupName=log_group,
                        logStreamNamePrefix=log_stream
                    )
                    if response['logStreams']:
                        sequence_token = response['logStreams'][0].get('uploadSequenceToken')
                except Exception:
                    pass
                
                # Put log events
                put_params = {
                    'logGroupName': log_group,
                    'logStreamName': log_stream,
                    'logEvents': batch
                }
                if sequence_token:
                    put_params['sequenceToken'] = sequence_token
                
                client.put_log_events(**put_params)
        
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"CloudWatch error: {str(e)}")
        
        logger.debug(f"Sent {len(logs)} logs to CloudWatch for {integration.name}")
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test CloudWatch connection."""
        start_time = time.time()
        
        try:
            credentials = await self.get_credentials(integration)
            access_key = credentials.get("access_key_id")
            secret_key = credentials.get("secret_access_key")
            
            if not access_key or not secret_key:
                return {"success": False, "message": "AWS credentials not found"}
            
            config = integration.config
            region = config.get("region", "us-east-1")
            log_group = config.get("log_group")
            
            if not log_group:
                return {"success": False, "message": "Log group not configured"}
            
            # Test connection by listing log groups
            client = boto3.client(
                'logs',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
            
            # Try to describe the log group
            client.describe_log_groups(logGroupNamePrefix=log_group)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "message": "Connection successful",
                "response_time_ms": response_time_ms
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }


# ─── Tier 2 Integrations (Stubbed) ───

class ElasticsearchHandler(IntegrationHandler):
    """Handler for Elasticsearch/OpenSearch integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to Elasticsearch/OpenSearch."""
        logger.info(f"Elasticsearch integration stub - would send {len(logs)} logs")
        # TODO: Implement Elasticsearch bulk API integration
        pass
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test Elasticsearch connection."""
        return {
            "success": False,
            "message": "Elasticsearch integration not yet implemented"
        }


class AzureMonitorHandler(IntegrationHandler):
    """Handler for Azure Monitor integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to Azure Monitor."""
        logger.info(f"Azure Monitor integration stub - would send {len(logs)} logs")
        # TODO: Implement Azure Monitor Data Collector API
        pass
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test Azure Monitor connection."""
        return {
            "success": False,
            "message": "Azure Monitor integration not yet implemented"
        }


class GoogleCloudLoggingHandler(IntegrationHandler):
    """Handler for Google Cloud Logging integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to Google Cloud Logging."""
        logger.info(f"GCP Logging integration stub - would send {len(logs)} logs")
        # TODO: Implement Google Cloud Logging client library
        pass
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test Google Cloud Logging connection."""
        return {
            "success": False,
            "message": "Google Cloud Logging integration not yet implemented"
        }


class WebhookHandler(IntegrationHandler):
    """Handler for generic webhook integration."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to webhook endpoint."""
        logger.info(f"Webhook integration stub - would send {len(logs)} logs")
        # TODO: Implement generic webhook posting
        pass
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test webhook connection."""
        return {
            "success": False,
            "message": "Webhook integration not yet implemented"
        }


class CloudStorageHandler(IntegrationHandler):
    """Handler for cloud storage batch exports (S3, GCS, Azure Blob)."""
    
    async def send_logs(self, integration: LogIntegration, logs: List[PlatformLog]):
        """Send logs to cloud storage."""
        logger.info(f"Cloud Storage integration stub - would send {len(logs)} logs")
        # TODO: Implement batch export to cloud storage
        pass
    
    async def test_connection(self, integration: LogIntegration) -> Dict[str, Any]:
        """Test cloud storage connection."""
        return {
            "success": False,
            "message": "Cloud Storage integration not yet implemented"
        }


# ─── Integration Registry ───

class IntegrationRegistry:
    """Registry for log integration handlers."""
    
    def __init__(self):
        self.handlers = {
            # Tier 1 - Fully implemented
            "datadog": DatadogHandler(),
            "splunk": SplunkHandler(),
            "cloudwatch": CloudWatchHandler(),
            
            # Tier 2 - Stubbed
            "elasticsearch": ElasticsearchHandler(),
            "opensearch": ElasticsearchHandler(),  # Same handler
            "azure_monitor": AzureMonitorHandler(),
            "google_cloud_logging": GoogleCloudLoggingHandler(),
            "webhook": WebhookHandler(),
            "s3": CloudStorageHandler(),
            "gcs": CloudStorageHandler(),
            "azure_blob": CloudStorageHandler(),
        }
    
    def get_handler(self, integration_type: str) -> Optional[IntegrationHandler]:
        """Get handler for integration type."""
        return self.handlers.get(integration_type)
    
    def list_types(self) -> List[str]:
        """List available integration types."""
        return list(self.handlers.keys())
    
    def is_implemented(self, integration_type: str) -> bool:
        """Check if integration type is fully implemented."""
        implemented = ["datadog", "splunk", "cloudwatch"]
        return integration_type in implemented


# Global registry instance
integration_registry = IntegrationRegistry()