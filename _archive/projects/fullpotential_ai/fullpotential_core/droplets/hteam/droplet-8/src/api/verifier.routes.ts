// src/api/verifier.routes.ts
import { FastifyInstance } from 'fastify';
import { AirtableService } from '../services/airtable.service';
import { SupabaseService } from '../services/supabase.service';
import { TesterService } from '../services/tester.service';
import { createHmac } from 'crypto';
import { env } from '../config/env';

// Initialize services
const airtableService = new AirtableService();
const supabaseService = new SupabaseService();

export async function verifierRoutes(app: FastifyInstance) {

  // ✅ 1. Health
  app.get('/verifier/health', async (req, reply) => {
    try {
      // Test Airtable connection by listing Submissions table metadata
      const airtableTest = await airtableService.testConnection();
      
      // Test Supabase connection with a small test upload
      const supabaseTest = await supabaseService.testConnection();
      
      return {
        status: 'ok',
        service: 'Verifier',
        timestamp: new Date().toISOString(),
        connections: {
          airtable: airtableTest ? 'connected' : 'disconnected',
          supabase: supabaseTest ? 'connected' : 'disconnected'
        }
      };
    } catch (error) {
      return reply.status(500).send({
        status: 'error',
        service: 'Verifier',
        timestamp: new Date().toISOString(),
        connections: {
          airtable: error instanceof Error && error.message.includes('Airtable') ? 'disconnected' : 'connected',
          supabase: error instanceof Error && error.message.includes('Supabase') ? 'disconnected' : 'connected'
        },
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // ✅ 2. Submit
  app.post('/verifier/submit', async (req, reply) => {
    try {
      const { base_url, dev_name, project_id, api_key ,submission_id,started_at} = req.body as any;

      if (!base_url || !dev_name || !project_id) {
        return reply.status(400).send({ 
          status: 'error',
          error: 'Missing required fields: base_url, dev_name, and project_id are required' 
        });
      }

      const submissionId = await airtableService.createSubmission({
        "Project": project_id,
        "Developer Name": dev_name,
        "Base URL": base_url,
        // "API Key": api_key,
        "Status": 'Pending',
        "Submission ID": submission_id,
        "Started At": started_at,
      });

      if (!submissionId) {
        return reply.status(500).send({
          status: 'error',
          error: 'Failed to create submission record'
        });
      }

      return {
        status: 'success',
        submission_id: submissionId
      };
    } catch (error) {
      return reply.status(500).send({
        status: 'error',
        error: error
      });
    }
  });

  // ✅ 3. Verify
  app.post('/verifier/verify', async (req, reply) => {
    try {
      const { submission_id, base_url } = req.body as any;

      if (!submission_id || !base_url) {
        return reply.status(400).send({ 
          status: 'error',
          error: 'Missing submission_id or base_url'
        });
      }

      if (!env.VERIFIER_SECRET) {
        return reply.status(500).send({
          status: 'error',
          error: 'Server configuration error: VERIFIER_SECRET is not defined'
        });
      }

      const assignment = {
        endpoints: [
          { path: '/health', expect: { status: 200 } },
          { path: '/register', method: 'POST', expect: { status: 200 } },
        ],
      };

      const testerService = new TesterService();
      const result = await testerService.runChecks(base_url, assignment);
      const score = (result.passed / result.total) * 100;
      const status = score >= 80 ? 'Pass' : 'Fail';
      
      const token = createHmac('sha256', env.VERIFIER_SECRET)
        .update(`${submission_id}|${status}|${score}|${Date.now()}`)
        .digest('hex');

      const logsUrl = await supabaseService.uploadJsonLog(submission_id, result);

      await airtableService.updateSubmission(submission_id, {
        "Status": status,
        "Score": score,
        "Token": token,
        "Logs URL": logsUrl,
        "Finished At": new Date().toISOString(),
      });

      return {
        status: 'success',
        submission_id,
        test_status: status,
        score,
        token,
        logs_url: logsUrl
      };
    } catch (error) {
      return reply.status(500).send({
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error during verification'
      });
    }
  });

  // ✅ 4. Result
  app.get('/verifier/result/:id', async (req, reply) => {
    try {
      const { id } = req.params as any;
      const submission = await airtableService.findSubmission(id);

      if (!submission) {
        return reply.status(404).send({
          status: 'error',
          error: 'Submission not found'
        });
      }

      return {
        status: 'success',
        submission_id: submission.id,
        airtable_id: submission.id,
        test_status: submission.fields.Status,
        score: submission.fields.Score,
        logs_url: submission.fields.Logs_URL
      };
    } catch (error) {
      return reply.status(500).send({
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error while fetching result'
      });
    }
  });
}
