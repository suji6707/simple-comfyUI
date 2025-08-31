'use client';

import { useState } from 'react';
import { Template } from '@/lib/api-client';
import { useGenerationStore } from '@/lib/stores/generation-store';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Slider } from './ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { Badge } from './ui/badge';
import { Loader2, ChevronDown, Settings, Wand2, Image as ImageIcon } from 'lucide-react';
import { toast } from './ui/use-toast';

interface GenerationFormProps {
  template: Template | null;
  className?: string;
}

interface FormData {
  prompt: string;
  negativePrompt: string;
  width: number;
  height: number;
  numImages: number;
  steps: number;
  cfgScale: number;
  seed: number | null;
  [key: string]: any;
}

const RESOLUTION_PRESETS = [
  { label: 'Square (1:1)', width: 1024, height: 1024, value: '1024x1024' },
  { label: 'Portrait (3:4)', width: 768, height: 1024, value: '768x1024' },
  { label: 'Landscape (4:3)', width: 1024, height: 768, value: '1024x768' },
  { label: 'Wide (16:9)', width: 1024, height: 576, value: '1024x576' },
  { label: 'Tall (9:16)', width: 576, height: 1024, value: '576x1024' },
];

export function GenerationForm({ template, className }: GenerationFormProps) {
  const { submitGeneration, isLoading, error } = useGenerationStore();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    prompt: '',
    negativePrompt: '',
    width: 1024,
    height: 1024,
    numImages: 1,
    steps: 50,
    cfgScale: 7.5,
    seed: null,
  });

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleResolutionChange = (value: string) => {
    const preset = RESOLUTION_PRESETS.find(p => p.value === value);
    if (preset) {
      handleInputChange('width', preset.width);
      handleInputChange('height', preset.height);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!template) {
      toast({
        title: 'No template selected',
        description: 'Please select a template first.',
        variant: 'destructive',
      });
      return;
    }

    if (!formData.prompt.trim()) {
      toast({
        title: 'Prompt required',
        description: 'Please enter a prompt for your image.',
        variant: 'destructive',
      });
      return;
    }

    try {
      const parameters = {
        width: formData.width,
        height: formData.height,
        num_images: formData.numImages,
        steps: formData.steps,
        cfg_scale: formData.cfgScale,
        negative_prompt: formData.negativePrompt,
        ...(formData.seed && { seed: formData.seed }),
      };

      const jobId = await submitGeneration(formData.prompt, template.id, parameters);
      
      if (jobId) {
        toast({
          title: 'Generation started!',
          description: 'Your image is being generated. You can track the progress below.',
        });
        
        // Reset form
        setFormData(prev => ({
          ...prev,
          prompt: '',
          negativePrompt: '',
          seed: null,
        }));
      }
    } catch (error) {
      console.error('Generation failed:', error);
    }
  };

  if (!template) {
    return (
      <Card className={cn('w-full', className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center text-gray-500">
            <ImageIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Select a template to begin</p>
            <p className="text-sm">Choose from our collection of AI generation styles</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5" />
              Generate with {template.name}
            </CardTitle>
            <CardDescription>{template.description}</CardDescription>
          </div>
          <Badge variant="outline">{template.category}</Badge>
        </div>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Prompt Input */}
          <div className="space-y-2">
            <Label htmlFor="prompt" className="text-sm font-medium">
              Prompt <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="prompt"
              placeholder={`Describe what you want to generate using the ${template.name} style...`}
              value={formData.prompt}
              onChange={(e) => handleInputChange('prompt', e.target.value)}
              className="min-h-[100px] resize-none"
              disabled={isLoading}
              required
            />
            <p className="text-xs text-gray-500">
              Be specific and descriptive for best results
            </p>
          </div>

          {/* Quick Settings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Resolution */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Resolution</Label>
              <Select
                value={`${formData.width}x${formData.height}`}
                onValueChange={handleResolutionChange}
                disabled={isLoading}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RESOLUTION_PRESETS.map((preset) => (
                    <SelectItem key={preset.value} value={preset.value}>
                      {preset.label} ({preset.value})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Number of Images */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                Images ({formData.numImages})
              </Label>
              <Slider
                value={[formData.numImages]}
                onValueChange={([value]) => handleInputChange('numImages', value)}
                min={1}
                max={4}
                step={1}
                className="w-full"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Advanced Settings */}
          <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Settings className="h-4 w-4" />
                  Advanced Settings
                </span>
                <ChevronDown
                  className={cn(
                    'h-4 w-4 transition-transform',
                    showAdvanced && 'rotate-180'
                  )}
                />
              </Button>
            </CollapsibleTrigger>

            <CollapsibleContent className="space-y-4 mt-4">
              {/* Negative Prompt */}
              <div className="space-y-2">
                <Label htmlFor="negative-prompt" className="text-sm font-medium">
                  Negative Prompt
                </Label>
                <Textarea
                  id="negative-prompt"
                  placeholder="What you don't want in the image..."
                  value={formData.negativePrompt}
                  onChange={(e) => handleInputChange('negativePrompt', e.target.value)}
                  className="min-h-[80px] resize-none"
                  disabled={isLoading}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Steps */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    Steps ({formData.steps})
                  </Label>
                  <Slider
                    value={[formData.steps]}
                    onValueChange={([value]) => handleInputChange('steps', value)}
                    min={10}
                    max={150}
                    step={1}
                    className="w-full"
                    disabled={isLoading}
                  />
                  <p className="text-xs text-gray-500">Higher = better quality, slower</p>
                </div>

                {/* CFG Scale */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    Guidance ({formData.cfgScale})
                  </Label>
                  <Slider
                    value={[formData.cfgScale]}
                    onValueChange={([value]) => handleInputChange('cfgScale', value)}
                    min={1}
                    max={20}
                    step={0.5}
                    className="w-full"
                    disabled={isLoading}
                  />
                  <p className="text-xs text-gray-500">How closely to follow the prompt</p>
                </div>
              </div>

              {/* Seed */}
              <div className="space-y-2">
                <Label htmlFor="seed" className="text-sm font-medium">
                  Seed (Optional)
                </Label>
                <Input
                  id="seed"
                  type="number"
                  placeholder="Random seed for reproducibility"
                  value={formData.seed || ''}
                  onChange={(e) => handleInputChange('seed', e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isLoading}
                />
                <p className="text-xs text-gray-500">
                  Leave empty for random results
                </p>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Error Display */}
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={isLoading || !formData.prompt.trim()}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="h-4 w-4 mr-2" />
                Generate {formData.numImages} Image{formData.numImages > 1 ? 's' : ''}
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}