import { Injectable } from '@nestjs/common';
import { AirtableService } from '../../airtable.service';
import { SupabaseService } from '../../supabase.service';
import { TesterService } from '../../tester.service';
import * as crypto from 'crypto';

@Injectable()
export class VerifierService {
  constructor(
    private airtable: AirtableService,
    private supabase: SupabaseService,
    private tester: TesterService
  ) {}

  makeToken(submissionId: string, status: string, score: number) {
    const msg = `${submissionId}|${status}|${score}|${Date.now()}`;
    return crypto
      .createHmac('sha256', process.env.VERIFIER_SECRET!)
      .update(msg)
      .digest('hex');
  }

  async verifySubmission(submission: any, assignment: any) {
    const submissionId = await this.airtable.createSubmission({
      Dev_Name: submission.dev_name,
      Project_ID: submission.project_id,
      Base_URL: submission.base_url,
      Started_At: new Date().toISOString(),
      Status: 'Pending',
    });

    const result = await this.tester.runChecks(submission.base_url, assignment);
    const score = (result.passed / result.total) * 100;
    const status = score >= 80 ? 'Pass' : 'Fail';
    const token = this.makeToken(submissionId, status, score);

    const logsUrl = await this.supabase.uploadJsonLog(submissionId, result);

    await this.airtable.updateSubmission(submissionId, {
      Status: status,
      Score: score,
      Token: token,
      Logs_URL: logsUrl,
      Finished_At: new Date().toISOString(),
    });

    return { submissionId, status, score, token, logsUrl };
  }
}
