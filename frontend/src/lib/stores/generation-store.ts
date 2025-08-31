import { create } from 'zustand';
import { Template, GenerationJob, GenerationParameters, apiClient } from '../api-client';

interface GenerationState {
  // Templates
  templates: Template[];
  selectedTemplate: Template | null;
  isLoading: boolean;
  error: string | null;

  // Jobs
  jobs: GenerationJob[];
  currentJob: GenerationJob | null;

  // Actions
  fetchTemplates: () => Promise<void>;
  selectTemplate: (template: Template) => void;
  submitGeneration: (prompt: string, parameters: GenerationParameters) => Promise<string | null>;
  fetchJobs: () => Promise<void>;
  fetchJobStatus: (jobId: string) => Promise<void>;
  clearError: () => void;
}

export const useGenerationStore = create<GenerationState>((set: any, get: any) => ({
  // Initial state
  templates: [],
  selectedTemplate: null,
  isLoading: false,
  error: null,
  jobs: [],
  currentJob: null,

  // Actions
  fetchTemplates: async () => {
    try {
      set({ isLoading: true, error: null });
      const templates = await apiClient.fetchTemplates();
      set({ templates, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch templates',
        isLoading: false 
      });
    }
  },

  selectTemplate: (template: Template) => {
    set({ selectedTemplate: template });
  },

  submitGeneration: async (prompt: string, parameters: GenerationParameters) => {
    try {
      set({ isLoading: true, error: null });
      const jobId = await apiClient.submitGeneration(prompt, parameters);
      
      // Start polling for job status
      const pollJob = async () => {
        try {
          const job = await apiClient.getJob(jobId);
          set({ currentJob: job });
          
          if (job.status === 'pending' || job.status === 'running') {
            setTimeout(pollJob, 2000); // Poll every 2 seconds
          } else {
            set({ isLoading: false });
            // Refresh jobs list
            get().fetchJobs();
          }
        } catch (error) {
          console.error('Error polling job status:', error);
          set({ isLoading: false });
        }
      };

      pollJob();
      return jobId;
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to submit generation',
        isLoading: false 
      });
      return null;
    }
  },

  fetchJobs: async () => {
    try {
      const jobs = await apiClient.getJobs();
      set({ jobs });
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  },

  fetchJobStatus: async (jobId: string) => {
    try {
      const job = await apiClient.getJob(jobId);
      const { jobs } = get();
      const updatedJobs = jobs.map((j: GenerationJob) => j.id === jobId ? job : j);
      set({ jobs: updatedJobs });
      
      if (get().currentJob?.id === jobId) {
        set({ currentJob: job });
      }
    } catch (error) {
      console.error('Error fetching job status:', error);
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));