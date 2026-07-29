import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Requirement {
  name: string;
  description: string;
  required: boolean;
  met: boolean;
  current_version: string | null;
  message: string;
}

interface RequirementCheck {
  overall_status: string;
  requirements: Requirement[];
  missing_required: string[];
  warnings: string[];
}

interface DeploymentStep {
  step: string;
  success: boolean;
  output?: string;
  error?: string | null;
}

interface DeploymentResult {
  status: string;
  steps: DeploymentStep[];
  errors: string[];
  start_time: string;
  end_time: string;
}

export function DeploymentManager() {
  const [requirements, setRequirements] = useState<RequirementCheck | null>(null);
  const [deploymentStatus, setDeploymentStatus] = useState<string>('idle');
  const [deploymentResult, setDeploymentResult] = useState<DeploymentResult | null>(null);
  const [validationResult, setValidationResult] = useState<any>(null);

  useEffect(() => {
    checkRequirements();
  }, []);

  const checkRequirements = async () => {
    try {
      const response = await fetch('/api/v1/admin/deploy/requirements');
      const data = await response.json();
      setRequirements(data);
    } catch (error) {
      console.error('Failed to check requirements:', error);
    }
  };

  const deployLocalInfrastructure = async () => {
    setDeploymentStatus('deploying');
    try {
      const response = await fetch('/api/v1/admin/deploy/local', { method: 'POST' });
      const data = await response.json();
      setDeploymentResult(data);
      setDeploymentStatus(data.status);
    } catch (error) {
      console.error('Deployment failed:', error);
      setDeploymentStatus('error');
    }
  };

  const validateDeployment = async () => {
    try {
      const response = await fetch('/api/v1/admin/deploy/validate');
      const data = await response.json();
      setValidationResult(data);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  if (!requirements) {
    return <div>Loading deployment requirements...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">V5 Deployment Manager</h1>
        <Badge variant={requirements.overall_status === 'ready' ? 'default' : 'destructive'}>
          {requirements.overall_status === 'ready' ? 'Ready to Deploy' : 'Requirements Not Met'}
        </Badge>
      </div>

      {/* Requirements Check */}
      <Card>
        <CardHeader>
          <CardTitle>Deployment Requirements</CardTitle>
        </CardHeader>
        <CardContent>
          {requirements.missing_required.length > 0 && (
            <Alert className="mb-4" variant="destructive">
              <AlertDescription>
                Missing required dependencies: {requirements.missing_required.join(', ')}
              </AlertDescription>
            </Alert>
          )}
          
          <div className="space-y-3">
            {requirements.requirements.map((req) => (
              <div key={req.name} className="flex items-center justify-between p-3 border rounded">
                <div>
                  <div className="font-medium">{req.name}</div>
                  <div className="text-sm text-gray-500">{req.description}</div>
                  {req.current_version && (
                    <div className="text-xs text-gray-400">Version: {req.current_version}</div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={req.met ? 'default' : 'destructive'}>
                    {req.met ? 'Met' : 'Not Met'}
                  </Badge>
                  {req.required && <Badge variant="outline">Required</Badge>}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Deployment Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Deployment Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button 
              onClick={deployLocalInfrastructure}
              disabled={requirements.overall_status !== 'ready' || deploymentStatus === 'deploying'}
            >
              {deploymentStatus === 'deploying' ? 'Deploying...' : 'Deploy Local Infrastructure'}
            </Button>
            <Button onClick={validateDeployment} variant="outline">
              Validate Deployment
            </Button>
            <Button onClick={checkRequirements} variant="outline">
              Recheck Requirements
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Deployment Results */}
      {deploymentResult && (
        <Card>
          <CardHeader>
            <CardTitle>Deployment Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {deploymentResult.steps.map((step, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded">
                  <div>
                    <div className="font-medium">{step.step}</div>
                    {step.output && (
                      <div className="text-sm text-gray-500">{step.output}</div>
                    )}
                    {step.error && (
                      <div className="text-sm text-red-500">{step.error}</div>
                    )}
                  </div>
                  <Badge variant={step.success ? 'default' : 'destructive'}>
                    {step.success ? 'Success' : 'Failed'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Validation Results */}
      {validationResult && (
        <Card>
          <CardHeader>
            <CardTitle>Validation Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {validationResult.components.map((comp: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded">
                  <div>
                    <div className="font-medium">{comp.component}</div>
                    <div className="text-sm text-gray-500">{comp.details}</div>
                  </div>
                  <Badge variant={comp.status === 'healthy' ? 'default' : 'destructive'}>
                    {comp.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}