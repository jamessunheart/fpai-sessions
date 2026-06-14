import { Injectable } from '@nestjs/common';
import { createClient } from '@supabase/supabase-js';

@Injectable()
export class SupabaseService {
  private client;
  private bucket;

  constructor() {
    this.client = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!);
    this.bucket = process.env.SUPABASE_BUCKET || 'verifier-logs';
  }

  async uploadJsonLog(submissionId: string, data: any) {
    const filename = `logs/${submissionId}-${Date.now()}.json`;
    const json = JSON.stringify(data, null, 2);
    const { error } = await this.client.storage.from(this.bucket)
      .upload(filename, Buffer.from(json), { contentType: 'application/json', upsert: true });
    if (error) throw error;
    const { data: publicUrlData } = this.client.storage.from(this.bucket).getPublicUrl(filename);
    return publicUrlData.publicUrl;
  }

  async testConnection(): Promise<boolean> {
    try {
      // Try to list bucket contents as a connection test
      const { data, error } = await this.client.storage.from(this.bucket).list('', { limit: 1 });
      if (error) throw error;
      return true;
    } catch (error) {
      console.error('Supabase connection test failed:', error);
      return false;
    }
  }
}
