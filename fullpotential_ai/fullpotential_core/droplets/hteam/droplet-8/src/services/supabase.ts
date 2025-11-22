// src/services/supabase.ts
import { createClient } from '@supabase/supabase-js';
import { env } from '../config/env';

const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_KEY);

export async function uploadLogToSupabase(filename: string, data: any) {
  const filePath = `${filename}.json`;
  const { error } = await supabase.storage
    .from(env.SUPABASE_BUCKET)
    .upload(filePath, JSON.stringify(data, null, 2), { upsert: true });

  if (error) {
    console.error('❌ Supabase upload failed:', error);
    return null;
  }

  const { data: publicUrl } = supabase.storage.from(env.SUPABASE_BUCKET).getPublicUrl(filePath);
  return publicUrl.publicUrl;
}
