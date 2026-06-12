// src/config/env.ts
import * as dotenv from 'dotenv';
dotenv.config();

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Environment variable ${name} is required`);
  }
  return value;
}

export const env = {
  PORT: process.env.PORT || 3000,
  VERIFIER_SECRET: requireEnv('VERIFIER_SECRET'),
  AIRTABLE_PERSONAL_TOKEN: requireEnv('AIRTABLE_PERSONAL_TOKEN'),
  AIRTABLE_BASE_ID: requireEnv('AIRTABLE_BASE_ID'),
  SUPABASE_URL: requireEnv('SUPABASE_URL'),
  SUPABASE_KEY: requireEnv('SUPABASE_KEY'),
  SUPABASE_BUCKET: requireEnv('SUPABASE_BUCKET'),
};

// 👇 You can safely console.log them (mask sensitive parts)
console.log('Loaded environment:');
console.log({
  PORT: env.PORT,
  VERIFIER_SECRET: env.VERIFIER_SECRET?.slice(0, 5) + '...',
  AIRTABLE_PERSONAL_TOKEN: env.AIRTABLE_PERSONAL_TOKEN?.slice(0, 5) + '...',
  AIRTABLE_BASE_ID: env.AIRTABLE_BASE_ID,
  SUPABASE_URL: env.SUPABASE_URL,
  SUPABASE_KEY: env.SUPABASE_KEY?.slice(0, 5) + '...',
  SUPABASE_BUCKET: env.SUPABASE_BUCKET,
});
