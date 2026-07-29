import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface V5SystemStatus {
  deployment_mode: string;
  cpu_only_mode: boolean;
  local_database: boolean;
  local_redis: boolean;
  cpu_ml_enabled: boolean;
  system_health: string;
  overall_progress: number;
}

interface V5Metrics {
  cpu_usage: number;
  memory_usage: number;
  ml_latency_ms: number;
  ml_throughput: number;
  pattern_accuracy: number;
  learning_progress: number;
}

interface Milestone {
  id: string;
  name: string;
  status: string;
  progress: number;
  completed_at: string;
}

export function V5AdminDashboard() {
  const [systemStatus, setSystemStatus] = useState<V5SystemStatus | null>(null);
  const [metrics, setMetrics] = useState<V5Metrics | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchV5Data();
  }, []);

  const fetchV5Data = async () => {
    try {
      const [statusRes, metricsRes, milestonesRes] = await Promise.all([
        fetch('/api/v1/v5/system/status'),
        fetch('/api/v1/v5/metrics'),
        fetch('/api/v1/v5/milestones')
      ]);

      const status = await statusRes.json();
      const metricsData = await metricsRes.json();
      const milestonesData = await milestonesRes.json();

      setSystemStatus(status);
      setMetrics(metricsData);
      setMilestones(milestonesData.milestones || []);
    } catch (error) {
      console.error('Failed to fetch V5 data:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerDiscovery = async () => {
    try {
      await fetch('/api/v1/v5/pattern/discovery', { method: 'POST' });
      fetchV5Data();
    } catch (error) {
      console.error('Failed to trigger discovery:', error);
    }
  };

  if (loading) {
    return <div>Loading V5 Admin Dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">V5 Free-Tier Administration</h1>
        <Badge variant="default">V5 Transformation</Badge>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Deployment Mode</div>
              <div className="font-semibold">{systemStatus?.deployment_mode || 'local'}</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">CPU Only Mode</div>
              <div className="font-semibold">{systemStatus?.cpu_only_mode ? 'Enabled' : 'Disabled'}</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Local Database</div>
              <div className="font-semibold">{systemStatus?.local_database ? 'Active' : 'Inactive'}</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Local Redis</div>
              <div className="font-semibold">{systemStatus?.local_redis ? 'Active' : 'Inactive'}</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">CPU ML Enabled</div>
              <div className="font-semibold">{systemStatus?.cpu_ml_enabled ? 'Enabled' : 'Disabled'}</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">System Health</div>
              <div className="font-semibold">{systemStatus?.system_health || 'healthy'}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* V5 Progress */}
      <Card>
        <CardHeader>
          <CardTitle>V5 Transformation Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="flex justify-between mb-2">
              <span>Overall Progress</span>
              <span className="font-semibold">{systemStatus?.overall_progress || 35}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full" 
                style={{ width: `${systemStatus?.overall_progress || 35}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">CPU Usage</div>
              <div className="text-2xl font-bold">{metrics?.cpu_usage?.toFixed(1) || 0}%</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Memory Usage</div>
              <div className="text-2xl font-bold">{metrics?.memory_usage?.toFixed(1) || 0}%</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">ML Latency</div>
              <div className="text-2xl font-bold">{metrics?.ml_latency_ms?.toFixed(1) || 0}ms</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">ML Throughput</div>
              <div className="text-2xl font-bold">{metrics?.ml_throughput || 0}/s</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Pattern Accuracy</div>
              <div className="text-2xl font-bold">{(metrics?.pattern_accuracy * 100)?.toFixed(1) || 0}%</div>
            </div>
            <div className="p-3 border rounded">
              <div className="text-sm text-gray-500">Learning Progress</div>
              <div className="text-2xl font-bold">{(metrics?.learning_progress * 100)?.toFixed(1) || 0}%</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Milestones */}
      <Card>
        <CardHeader>
          <CardTitle>V5 Milestones</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {milestones.map((milestone) => (
              <div key={milestone.id} className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="font-medium">{milestone.name}</div>
                  <div className="text-sm text-gray-500">{milestone.id}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={milestone.status === 'completed' ? 'default' : 'secondary'}>
                    {milestone.status}
                  </Badge>
                  <span className="text-sm">{milestone.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Admin Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button onClick={triggerDiscovery}>Trigger Pattern Discovery</Button>
            <Button variant="outline">Optimize CPU ML</Button>
            <Button variant="outline">Run Health Check</Button>
            <Button variant="outline">View System Logs</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}