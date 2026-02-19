"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Settings, TestTube, Trash2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface LogIntegration {
  id: string;
  name: string;
  integration_type: string;
  config: Record<string, any>;
  enabled: boolean;
  last_test_status: string | null;
  last_test_message: string | null;
  last_test_at: string | null;
  created_at: string;
  updated_at: string;
}

const IntegrationTypes = {
  datadog: { name: 'Datadog', icon: '🐶', implemented: true },
  splunk: { name: 'Splunk', icon: '🔍', implemented: true },
  cloudwatch: { name: 'AWS CloudWatch', icon: '☁️', implemented: true },
  elasticsearch: { name: 'Elasticsearch', icon: '🔍', implemented: false },
  opensearch: { name: 'OpenSearch', icon: '🔍', implemented: false },
  azure_monitor: { name: 'Azure Monitor', icon: '📊', implemented: false },
  google_cloud_logging: { name: 'Google Cloud Logging', icon: '📊', implemented: false },
  webhook: { name: 'Webhook', icon: '🔗', implemented: false },
  s3: { name: 'AWS S3', icon: '🪣', implemented: false },
  gcs: { name: 'Google Cloud Storage', icon: '🪣', implemented: false },
  azure_blob: { name: 'Azure Blob Storage', icon: '🪣', implemented: false },
};

export default function LogIntegrationsPage() {
  const [integrations, setIntegrations] = useState<LogIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  // Form state for creating integrations
  const [formData, setFormData] = useState({
    name: '',
    integration_type: '',
    config: '{}',
    credentials: '{}',
    enabled: true
  });

  const fetchIntegrations = async () => {
    try {
      const response = await fetch('/api/logs/integrations');
      if (!response.ok) {
        throw new Error('Failed to fetch integrations');
      }
      const data = await response.json();
      setIntegrations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch integrations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const createIntegration = async () => {
    try {
      const config = JSON.parse(formData.config);
      const credentials = JSON.parse(formData.credentials);

      const response = await fetch('/api/logs/integrations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          integration_type: formData.integration_type,
          config,
          credentials,
          enabled: formData.enabled
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create integration');
      }

      await fetchIntegrations();
      setCreateDialogOpen(false);
      setFormData({
        name: '',
        integration_type: '',
        config: '{}',
        credentials: '{}',
        enabled: true
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create integration');
    }
  };

  const testIntegration = async (integrationId: string) => {
    setTestingId(integrationId);
    try {
      const response = await fetch(`/api/logs/integrations/${integrationId}/test`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to test integration');
      }

      await fetchIntegrations(); // Refresh to get updated test status
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to test integration');
    } finally {
      setTestingId(null);
    }
  };

  const toggleIntegration = async (integrationId: string, enabled: boolean) => {
    try {
      const response = await fetch(`/api/logs/integrations/${integrationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled })
      });

      if (!response.ok) {
        throw new Error('Failed to update integration');
      }

      await fetchIntegrations();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update integration');
    }
  };

  const deleteIntegration = async (integrationId: string) => {
    if (!confirm('Are you sure you want to delete this integration?')) {
      return;
    }

    try {
      const response = await fetch(`/api/logs/integrations/${integrationId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete integration');
      }

      await fetchIntegrations();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete integration');
    }
  };

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getConfigExample = (type: string) => {
    const examples = {
      datadog: {
        config: { site: "datadoghq.com", service: "bonito", source: "bonito", tags: ["env:prod"] },
        credentials: { api_key: "your-datadog-api-key" }
      },
      splunk: {
        config: { host: "splunk.company.com", port: 8088, index: "main", source: "bonito" },
        credentials: { token: "your-hec-token" }
      },
      cloudwatch: {
        config: { region: "us-east-1", log_group: "/bonito/logs", log_stream: "platform" },
        credentials: { access_key_id: "your-access-key", secret_access_key: "your-secret-key" }
      }
    };
    return examples[type as keyof typeof examples] || { config: {}, credentials: {} };
  };

  const handleIntegrationTypeChange = (type: string) => {
    setFormData(prev => ({
      ...prev,
      integration_type: type,
      config: JSON.stringify(getConfigExample(type).config, null, 2),
      credentials: JSON.stringify(getConfigExample(type).credentials, null, 2)
    }));
  };

  if (loading) {
    return <div className="container mx-auto p-6">Loading integrations...</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Log Integrations</h1>
          <p className="text-gray-600">Configure external log destinations</p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Integration
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Log Integration</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Production Datadog"
                />
              </div>

              <div>
                <Label htmlFor="type">Integration Type</Label>
                <Select value={formData.integration_type} onValueChange={handleIntegrationTypeChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select integration type" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(IntegrationTypes).map(([key, value]) => (
                      <SelectItem key={key} value={key} disabled={!value.implemented}>
                        {value.icon} {value.name} {!value.implemented && '(Coming Soon)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="config">Configuration</Label>
                <Textarea
                  id="config"
                  value={formData.config}
                  onChange={(e) => setFormData(prev => ({ ...prev, config: e.target.value }))}
                  placeholder="JSON configuration"
                  rows={6}
                  className="font-mono text-sm"
                />
              </div>

              <div>
                <Label htmlFor="credentials">Credentials</Label>
                <Textarea
                  id="credentials"
                  value={formData.credentials}
                  onChange={(e) => setFormData(prev => ({ ...prev, credentials: e.target.value }))}
                  placeholder="JSON credentials"
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  checked={formData.enabled}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, enabled: checked }))}
                />
                <Label>Enable integration</Label>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={createIntegration}>
                  Create Integration
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="text-red-500">{error}</div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Active Integrations</CardTitle>
          <CardDescription>
            External services configured to receive log data
          </CardDescription>
        </CardHeader>
        <CardContent>
          {integrations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No integrations configured yet. Click "Add Integration" to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Test</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {integrations.map((integration) => (
                  <TableRow key={integration.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{integration.name}</div>
                        <div className="text-xs text-gray-500">
                          {integration.enabled ? (
                            <Badge variant="secondary" className="bg-green-100 text-green-800">
                              Enabled
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="bg-gray-100 text-gray-800">
                              Disabled
                            </Badge>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <span className="mr-2">
                          {IntegrationTypes[integration.integration_type as keyof typeof IntegrationTypes]?.icon || '⚙️'}
                        </span>
                        {IntegrationTypes[integration.integration_type as keyof typeof IntegrationTypes]?.name || integration.integration_type}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        {getStatusIcon(integration.last_test_status)}
                        <span className="ml-2 capitalize">
                          {integration.last_test_status || 'Not tested'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {integration.last_test_at ? (
                          <>
                            <div>{new Date(integration.last_test_at).toLocaleDateString()}</div>
                            <div className="text-xs text-gray-500">
                              {integration.last_test_message}
                            </div>
                          </>
                        ) : (
                          'Never'
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => testIntegration(integration.id)}
                          disabled={testingId === integration.id}
                        >
                          <TestTube className="w-3 h-3 mr-1" />
                          Test
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleIntegration(integration.id, !integration.enabled)}
                        >
                          <Settings className="w-3 h-3 mr-1" />
                          {integration.enabled ? 'Disable' : 'Enable'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteIntegration(integration.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}