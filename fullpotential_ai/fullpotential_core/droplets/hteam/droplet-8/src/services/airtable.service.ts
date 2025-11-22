import { Injectable } from '@nestjs/common';
import Airtable from 'airtable';
import { env } from '../config/env';

@Injectable()
export class AirtableService {
  private base: Airtable.Base;

  constructor() {
    // Use env from config instead of process.env directly
    this.base = new Airtable({
      apiKey: env.AIRTABLE_PERSONAL_TOKEN,
    }).base(env.AIRTABLE_BASE_ID);
  }

  async createSubmission(data: Record<string, any>) {
    const [record] = await this.base('Submissions').create([{ fields: data }]);
    return record.id;
  }

  async createCheck(data: Record<string, any>) {
    await this.base('Checks').create([{ fields: data }]);
  }

  async updateSubmission(id: string, data: Record<string, any>) {
    await this.base('Submissions').update([{ id, fields: data }]);
  }

  async findSubmission(id: string) {
    try {
      return await this.base('Submissions').find(id);
    } catch (error) {
      return null;
    }
  }

  async testConnection(): Promise<boolean> {
    try {
      console.log('Testing Airtable connection...');
      console.log('Base ID:', process.env.AIRTABLE_BASE_ID);
      
      // Try to select from the Submissions table
      try {
        await this.base('Submissions').select({ maxRecords: 1 }).firstPage();
        console.log('Successfully connected to Submissions table');
        return true;
      } catch (tableError) {
        // If we get a 404, the table doesn't exist
        if (tableError.error === 'NOT_FOUND') {
          console.error('Warning: Submissions table not found in the base');
          console.log('Please create a "Submissions" table in your Airtable base');
          return false;
        }
        // If it's another error, throw it to be caught by the outer try-catch
        throw tableError;
      }
    } catch (error) {
      console.error('Airtable connection test failed:', error);
      if (error instanceof Error) {
        console.error('Error details:', {
          message: error.message,
          name: error.name,
          stack: error.stack
        });
      }
      return false;
    }
  }
}
