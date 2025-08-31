export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  example_images?: string[];
  parameters?: Record<string, any>;
}

export interface GenerationJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'processing' | 'queued' | 'cancelled';
  progress: number;
  prompt: string;
  parameters: Record<string, any>;
  result?: string[];
  results?: Array<{
    id: string;
    image_url: string;
    thumbnail_url?: string;
  }>;
  error?: string;
  error_details?: string;
  created_at: string;
  updated_at: string;
  template?: Template;
  queue_position?: number;
}

export interface GenerationParameters {
  width: number;
  height: number;
  num_images: number;
  steps: number;
  cfg_scale: number;
  negative_prompt?: string;
  seed?: number;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    // Client-side environment variable access for Next.js
    this.baseUrl = (typeof window !== 'undefined' 
      ? (window as any).__NEXT_DATA__?.runtimeConfig?.NEXT_PUBLIC_API_URL 
      : process.env.NEXT_PUBLIC_API_URL) || 'http://localhost:8000';
  }

  async fetchTemplates(): Promise<Template[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/templates`);
      if (!response.ok) {
        throw new Error(`Failed to fetch templates: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching templates:', error);
      throw error;
    }
  }

  async submitGeneration(prompt: string, templateId: string, parameters: GenerationParameters): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          template_id: templateId,
          prompt,
          parameters,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to submit generation: ${response.statusText}`);
      }

      const result = await response.json();
      return result.job_id;
    } catch (error) {
      console.error('Error submitting generation:', error);
      throw error;
    }
  }

  async getJob(jobId: string): Promise<GenerationJob> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/generate/${jobId}/status`);
      if (!response.ok) {
        throw new Error(`Failed to fetch job: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching job:', error);
      throw error;
    }
  }

  async getJobs(): Promise<GenerationJob[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/history`);
      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching jobs:', error);
      throw error;
    }
  }

  async cancelJob(jobId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/generate/${jobId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to cancel job: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error cancelling job:', error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();