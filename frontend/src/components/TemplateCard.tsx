'use client';

import { Template } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Sparkles, Clock, Image as ImageIcon } from 'lucide-react';
import Image from 'next/image';

interface TemplateCardProps {
  template: Template;
  isSelected?: boolean;
  onSelect: (template: Template) => void;
  className?: string;
}

export function TemplateCard({ template, isSelected, onSelect, className }: TemplateCardProps) {
  const exampleImage = template.example_images?.[0];
  
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all duration-200 hover:shadow-lg hover:-translate-y-1',
        isSelected && 'ring-2 ring-blue-500 ring-offset-2',
        className
      )}
      onClick={() => onSelect(template)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="text-xs">
            {template.category}
          </Badge>
          {isSelected && (
            <Sparkles className="h-4 w-4 text-blue-500" />
          )}
        </div>
        
        <CardTitle className="text-lg">{template.name}</CardTitle>
        <CardDescription className="line-clamp-2">
          {template.description}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Example Image */}
        {exampleImage ? (
          <div className="relative aspect-square w-full overflow-hidden rounded-md bg-gray-100">
            <Image
              src={exampleImage}
              alt={`${template.name} example`}
              fill
              className="object-cover transition-transform hover:scale-105"
              onError={(e) => {
                // Fallback to placeholder on image load error
                const target = e.target as HTMLImageElement;
                target.src = `data:image/svg+xml;base64,${btoa(`
                  <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="#f3f4f6"/>
                    <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#9ca3af" font-family="system-ui" font-size="14">
                      ${template.name}
                    </text>
                  </svg>
                `)}`;
              }}
            />
          </div>
        ) : (
          <div className="relative aspect-square w-full overflow-hidden rounded-md bg-gray-100 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <ImageIcon className="h-12 w-12 mx-auto mb-2" />
              <p className="text-sm font-medium">{template.name}</p>
            </div>
          </div>
        )}
        
        {/* Template Stats */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>~30s</span>
          </div>
          <div className="flex items-center gap-1">
            <ImageIcon className="h-4 w-4" />
            <span>1-4 images</span>
          </div>
        </div>
        
        {/* Select Button */}
        <Button
          variant={isSelected ? "default" : "outline"}
          className="w-full"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(template);
          }}
        >
          {isSelected ? 'Selected' : 'Select Template'}
        </Button>
      </CardContent>
    </Card>
  );
}