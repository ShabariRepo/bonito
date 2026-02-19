"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Search, Filter, Download, Clock, AlertCircle, Info, AlertTriangle, XCircle } from 'lucide-react';

interface LogEntry {
  id: string;
  created_at: string;
  log_type: string;
  event_type: string;
  severity: string;
  user_id: string | null;
  resource_type: string | null;
  action: string | null;
  message: string | null;
  duration_ms: number | null;
  cost: number | null;
  metadata: Record<string, any> | null;
}

interface LogFilters {
  log_types: string[];
  event_types: string[];
  severities: string[];
  start_date?: string;
  end_date?: string;
  search?: string;
}

const LogTypeColors = {
  gateway: 'bg-blue-500',
  agent: 'bg-purple-500',
  auth: 'bg-green-500',
  admin: 'bg-orange-500',
  kb: 'bg-teal-500',
  deployment: 'bg-indigo-500',
  billing: 'bg-yellow-500'
};

const SeverityIcons = {
  debug: Info,
  info: Info,
  warn: AlertTriangle,
  error: AlertCircle,
  critical: XCircle
};

const SeverityColors = {
  debug: 'text-gray-500',
  info: 'text-blue-500',
  warn: 'text-yellow-500',
  error: 'text-red-500',
  critical: 'text-red-700'
};

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [filters, setFilters] = useState<LogFilters>({
    log_types: [],
    event_types: [],
    severities: []
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);

    try {
      const queryFilters = {
        ...filters,
        search: searchTerm || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      };

      const response = await fetch('/api/logs/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filters: queryFilters,
          limit,
          offset,
          sort_by: 'created_at',
          sort_order: 'desc'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }

      const data = await response.json();
      setLogs(data.logs);
      setTotalCount(data.total_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filters, limit, offset]);

  const handleSearch = () => {
    setOffset(0);
    fetchLogs();
  };

  const handleFilterChange = (key: keyof LogFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
    setOffset(0);
  };

  const exportLogs = async (format: 'csv' | 'json') => {
    try {
      const response = await fetch('/api/logs/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filters,
          export_format: format,
          include_metadata: true,
          email_when_complete: false
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start export');
      }

      const data = await response.json();
      alert(`Export job started (ID: ${data.id}). You can check the status in the exports section.`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start export');
    }
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatCost = (cost: number | null) => {
    if (!cost) return '-';
    return `$${cost.toFixed(4)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Platform Logs</h1>
          <p className="text-gray-600">Monitor and analyze platform activity</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => exportLogs('csv')}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => exportLogs('json')}>
            <Download className="w-4 h-4 mr-2" />
            Export JSON
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="w-5 h-5 mr-2" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Search</label>
              <div className="flex">
                <Input
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
                <Button variant="outline" className="ml-2" onClick={handleSearch}>
                  <Search className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Log Type</label>
              <Select
                value={filters.log_types[0] || 'all'}
                onValueChange={(value) => handleFilterChange('log_types', value === 'all' ? [] : [value])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="gateway">Gateway</SelectItem>
                  <SelectItem value="agent">Agent</SelectItem>
                  <SelectItem value="auth">Authentication</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="kb">Knowledge Base</SelectItem>
                  <SelectItem value="deployment">Deployment</SelectItem>
                  <SelectItem value="billing">Billing</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Severity</label>
              <Select
                value={filters.severities[0] || 'all'}
                onValueChange={(value) => handleFilterChange('severities', value === 'all' ? [] : [value])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All severities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Severities</SelectItem>
                  <SelectItem value="debug">Debug</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="warn">Warning</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Date Range</label>
              <Input
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Summary */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center text-sm text-gray-600">
          <Clock className="w-4 h-4 mr-1" />
          {loading ? 'Loading...' : `${totalCount} logs found`}
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm">Show:</span>
          <Select value={limit.toString()} onValueChange={(value) => setLimit(parseInt(value))}>
            <SelectTrigger className="w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
              <SelectItem value="200">200</SelectItem>
              <SelectItem value="500">500</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          {error ? (
            <div className="p-6 text-center text-red-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2" />
              {error}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => {
                  const SeverityIcon = SeverityIcons[log.severity as keyof typeof SeverityIcons] || Info;
                  
                  return (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-xs">
                        {formatDate(log.created_at)}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="secondary" 
                          className={`${LogTypeColors[log.log_type as keyof typeof LogTypeColors] || 'bg-gray-500'} text-white`}
                        >
                          {log.log_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-medium">{log.event_type}</span>
                        {log.action && (
                          <span className="ml-2 text-xs text-gray-500">({log.action})</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <SeverityIcon className={`w-4 h-4 mr-1 ${SeverityColors[log.severity as keyof typeof SeverityColors]}`} />
                          <span className="capitalize">{log.severity}</span>
                        </div>
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {log.message || '-'}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatDuration(log.duration_ms)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatCost(log.cost)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}

          {!loading && logs.length === 0 && (
            <div className="p-6 text-center text-gray-500">
              No logs found matching your criteria
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalCount > limit && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {offset + 1} to {Math.min(offset + limit, totalCount)} of {totalCount} logs
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={offset + limit >= totalCount}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}