// src/services/airtable.ts
import Airtable from 'airtable';
import { env } from '../config/env';

const base = new Airtable({ apiKey: env.AIRTABLE_PERSONAL_TOKEN }).base(env.AIRTABLE_BASE_ID);

export async function createAirtableRecord(table: string, fields: any) {
  try {
    const record = await base(table).create([{ fields }]);
    return record[0];
  } catch (err) {
    console.error('❌ Airtable create error:', err);
    return null;
  }
}

export async function updateAirtableRecord(table: string, id: string, fields: any) {
  try {
    const record = await base(table).update([{ id, fields }]);
    return record[0];
  } catch (err) {
    console.error('❌ Airtable update error:', err);
    return null;
  }
}

export async function getSubmissionById(table: string, id: string) {
  try {
    const record = await base(table).find(id);
    return record;
  } catch {
    return null;
  }
}
