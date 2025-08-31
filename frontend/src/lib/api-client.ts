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
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  prompt: string;
  parameters: Record<string, any>;
  result?: string[];
  error?: string;
  created_at: string;
  updated_at: string;
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
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  async fetchTemplates(): Promise<Template[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/templates`);
      if (!response.ok) {
        throw new Error(`Failed to fetch templates: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching templates:', error);
      throw error;
    }
  }

  async submitGeneration(prompt: string, parameters: GenerationParameters): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          ...parameters,
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
      const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`);
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
      const response = await fetch(`${this.baseUrl}/api/jobs`);
      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching jobs:', error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();