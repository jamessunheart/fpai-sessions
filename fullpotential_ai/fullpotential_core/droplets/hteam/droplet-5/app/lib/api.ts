import { Sprint, Cell, Proof, Heartbeat, DailyDigest, ApiResponse } from '../types';

const API_BASE = '/api/proxy';

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    try {
      const url = `${API_BASE}?endpoint=${encodeURIComponent(endpoint)}`;
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // Read Operations
  async getSprints(): Promise<ApiResponse<Sprint>> {
    return this.request<ApiResponse<Sprint>>('/sprints');
  }

  async getDashboard(): Promise<any> {
    return this.request('/dashboard');
  }

  async getProofs(): Promise<ApiResponse<Proof>> {
    return this.request<ApiResponse<Proof>>('/proof');
  }

  async getHeartbeats(): Promise<ApiResponse<Heartbeat>> {
    return this.request<ApiResponse<Heartbeat>>('/heartbeats');
  }

  async getDailyDigest(): Promise<any> {
    return this.request('/daily-digest', { method: 'POST' });
  }

  // Create Operations
  async createSprint(data: Partial<Sprint['fields']>): Promise<any> {
    return this.request('/sprints', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createCell(data: Partial<Cell['fields']>): Promise<any> {
    return this.request('/cells', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Update Operations
  async updateSprint(id: string, data: Partial<Sprint['fields']>): Promise<any> {
    return this.request(`/sprints/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Delete Operations
  async deleteSprint(id: string): Promise<any> {
    return this.request(`/sprints/${id}`, {
      method: 'DELETE',
    });
  }

  // Webhook Operations
  async sendWebhook(data: any): Promise<any> {
    return this.request('/webhook', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async sendProofWebhook(data: any): Promise<any> {
    return this.request('/proof-webhook', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async sendHeartbeatWebhook(data: any): Promise<any> {
    return this.request('/heartbeat-webhook', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Registry v2 Operations
  async getRegistryDroplets(): Promise<any> {
    return this.request('/registry/droplets');
  }
}

export const api = new ApiClient();