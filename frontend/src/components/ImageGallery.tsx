'use client';

import { useEffect } from 'react';
import { useGenerationStore } from '@/lib/stores/generation-store';
import { GenerationJob } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Download, Eye, Share2, Trash2, Clock, Image as ImageIcon } from 'lucide-react';

interface ImageGalleryProps {
  className?: string;
}

export function ImageGallery({ className }: ImageGalleryProps) {
  const { jobHistory, fetchJobHistory } = useGenerationStore();

  useEffect(() => {
    fetchJobHistory();
  }, [fetchJobHistory]);

  const completedJobs = jobHistory.filter(job => 
    job.status === 'completed' && job.results && job.results.length > 0
  );

  if (completedJobs.length === 0) {
    return (
      <Card className={cn('w-full', className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center text-gray-500">
            <ImageIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">No images yet</p>
            <p className="text-sm">Your generated images will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle>Your Gallery</CardTitle>
        <CardDescription>
          {completedJobs.length} generation{completedJobs.length > 1 ? 's' : ''} completed
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {completedJobs.map((job) => (
            <GenerationCard key={job.job_id} job={job} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface GenerationCardProps {
  job: GenerationJob;
}

function GenerationCard({ job }: GenerationCardProps) {
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

  if (!job.results || job.results.length === 0) return null;

  const primaryResult = job.results[0];
  const hasMultipleImages = job.results.length > 1;

  return (
    <div className="group border rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
      {/* Main Image */}
      <div className="relative aspect-square bg-gray-100">
        <img
          src={primaryResult.thumbnail_url || primaryResult.image_url}
          alt="Generated image"
          className="w-full h-full object-cover"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.src = `data:image/svg+xml;base64,${btoa(`
              <svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#f3f4f6"/>
                <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#9ca3af" font-family="system-ui" font-size="14">
                  Generated Image
                </text>
              </svg>
            `)}`;
          }}
        />
        
        {/* Overlay on Hover */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="flex gap-2">
            <Button size="sm" variant="secondary">
              <Eye className="h-4 w-4 mr-1" />
              View
            </Button>
            <Button size="sm" variant="secondary">
              <Download className="h-4 w-4 mr-1" />
              Download
            </Button>
            <Button size="sm" variant="secondary">
              <Share2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Multiple Images Badge */}
        {hasMultipleImages && (
          <div className="absolute top-2 right-2">
            <Badge variant="secondary" className="text-xs">
              +{job.results.length - 1}
            </Badge>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Prompt */}
        <div>
          <p className="text-sm font-medium line-clamp-2 mb-1">
            {job.prompt}
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock className="h-3 w-3" />
            <span>{formatTimeAgo(job.completed_at || job.created_at)}</span>
            {job.template && (
              <>
                <span>•</span>
                <Badge variant="outline" className="text-xs">
                  {job.template.name}
                </Badge>
              </>
            )}
          </div>
        </div>

        {/* Additional Images Grid */}
        {hasMultipleImages && (
          <div className="grid grid-cols-3 gap-1">
            {job.results.slice(1, 4).map((result, index) => (
              <div key={result.id} className="aspect-square relative">
                <img
                  src={result.thumbnail_url || result.image_url}
                  alt={`Generated image ${index + 2}`}
                  className="w-full h-full object-cover rounded border"
                />
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex gap-1">
            <Button size="sm" variant="ghost" className="h-8 px-2">
              <Eye className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="ghost" className="h-8 px-2">
              <Download className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="ghost" className="h-8 px-2">
              <Share2 className="h-3 w-3" />
            </Button>
          </div>
          <Button size="sm" variant="ghost" className="h-8 px-2 text-red-500 hover:text-red-600">
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}