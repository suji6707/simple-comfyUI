'use client';

import React, { useEffect } from 'react';
import { useGenerationStore } from '@/lib/stores/generation-store';
import { GenerationJob } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Clock, CheckCircle, XCircle, AlertCircle, Download, Eye } from 'lucide-react';

interface ProgressTrackerProps {
  className?: string;
}

export function ProgressTracker({ className }: ProgressTrackerProps) {
  const { jobs, fetchJobs } = useGenerationStore();

  useEffect(() => {
    // Fetch initial job history
    fetchJobs();
  }, [fetchJobs]);

  if (!jobs || jobs.length === 0) {
    return (
      <Card className={cn('w-full', className)}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center text-gray-500">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No active generations</p>
            <p className="text-xs">Start a generation to see progress here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle>Active Generations</CardTitle>
        <CardDescription>Track your ongoing image generations</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {jobs.map((job) => (
          <JobProgressCard key={job.id} job={job} />
        ))}
      </CardContent>
    </Card>
  );
}

interface JobProgressCardProps {
  job: GenerationJob;
}

function JobProgressCard({ job }: JobProgressCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'processing':
        return <AlertCircle className="h-4 w-4 text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'processing':
        return 'bg-blue-500';
      default:
        return 'bg-gray-400';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {getStatusIcon(job.status)}
            <Badge variant="secondary" className={cn('text-xs', getStatusColor(job.status))}>
              {job.status.toUpperCase()}
            </Badge>
          </div>
          <p className="text-sm font-medium truncate mb-1">{job.prompt}</p>
          <p className="text-xs text-gray-500">
            Started {formatTimeAgo(job.created_at)}
            {job.template && ` • ${job.template.name}`}
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      {job.status === 'processing' || job.status === 'queued' ? (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-600">
            <span>{job.status === 'queued' ? 'Queued' : 'Processing'}</span>
            <span>{job.progress}%</span>
          </div>
          <Progress value={job.progress} className="h-2" />
          {job.queue_position && job.queue_position > 0 && (
            <p className="text-xs text-gray-500">
              Position {job.queue_position} in queue
            </p>
          )}
        </div>
      ) : job.status === 'completed' && job.results ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-600">
              Generated {job.results.length} image{job.results.length > 1 ? 's' : ''}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                <Eye className="h-3 w-3 mr-1" />
                View
              </Button>
              <Button size="sm" variant="outline">
                <Download className="h-3 w-3 mr-1" />
                Download
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {job.results.slice(0, 4).map((result, index) => (
              <div key={result.id} className="aspect-square relative">
                <img
                  src={result.thumbnail_url || result.image_url}
                  alt={`Generated image ${index + 1}`}
                  className="w-full h-full object-cover rounded border"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.src = `data:image/svg+xml;base64,${btoa(`
                      <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
                        <rect width="100%" height="100%" fill="#f3f4f6"/>
                        <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#9ca3af" font-family="system-ui" font-size="12">
                          Image
                        </text>
                      </svg>
                    `)}`;
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      ) : job.status === 'failed' && (
        <div className="space-y-2">
          <div className="text-sm text-red-600 font-medium">Generation Failed</div>
          {job.error_details && (
            <p className="text-xs text-gray-600 bg-red-50 p-2 rounded border">
              {job.error_details}
            </p>
          )}
          <Button size="sm" variant="outline" className="text-red-600 border-red-200">
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}