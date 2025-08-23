'use client';

import { useState, useEffect } from 'react';
import { useGenerationStore } from '@/lib/stores/generation-store';
import { Template } from '@/lib/api-client';
import { TemplateCard } from '@/components/TemplateCard';
import { GenerationForm } from '@/components/GenerationForm';
import { ProgressTracker } from '@/components/ProgressTracker';
import { ImageGallery } from '@/components/ImageGallery';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search, Sparkles, History } from 'lucide-react';

export default function Home() {
  const { templates, selectedTemplate, fetchTemplates, selectTemplate, isLoading, error } = useGenerationStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Filter templates based on search and category
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !selectedCategory || template.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Get unique categories
  const categories = Array.from(new Set(templates.map(t => t.category))).sort();

  const handleTemplateSelect = (template: Template) => {
    selectTemplate(template);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <h1 className="text-xl font-semibold text-gray-900">ComfyUI Service</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="secondary" className="hidden sm:inline-flex">
                {templates.length} Templates Available
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Templates & Form */}
          <div className="lg:col-span-2 space-y-8">
            {/* Templates Section */}
            <div>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                    Choose Your Style
                  </h2>
                  <p className="text-gray-600">
                    Select a template to get started with AI image generation
                  </p>
                </div>
              </div>

              {/* Search and Filters */}
              <div className="space-y-4 mb-6">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search templates..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant={selectedCategory === null ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedCategory(null)}
                  >
                    All Categories
                  </Button>
                  {categories.map(category => (
                    <Button
                      key={category}
                      variant={selectedCategory === category ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedCategory(category)}
                    >
                      {category}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Templates Grid */}
              {isLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="bg-gray-200 rounded-lg h-64"></div>
                    </div>
                  ))}
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <p className="text-red-600">{error}</p>
                  <Button 
                    onClick={fetchTemplates}
                    className="mt-4"
                    variant="outline"
                  >
                    Try Again
                  </Button>
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500">No templates found</p>
                  {searchTerm && (
                    <Button
                      onClick={() => setSearchTerm('')}
                      variant="outline"
                      className="mt-2"
                    >
                      Clear search
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {filteredTemplates.map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      isSelected={selectedTemplate?.id === template.id}
                      onSelect={handleTemplateSelect}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Generation Form */}
            <GenerationForm template={selectedTemplate} />
          </div>

          {/* Right Column - Progress & Gallery */}
          <div className="space-y-8">
            <Tabs defaultValue="progress" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="progress">Progress</TabsTrigger>
                <TabsTrigger value="gallery">
                  <History className="h-4 w-4 mr-2" />
                  Gallery
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="progress" className="mt-6">
                <ProgressTracker />
              </TabsContent>
              
              <TabsContent value="gallery" className="mt-6">
                <ImageGallery />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}