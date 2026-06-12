// verifier.controller.ts
import { Controller, Post, Body, Get, Param, NotFoundException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiProperty } from '@nestjs/swagger';
import { AirtableService } from '../../airtable.service';
import { SupabaseService } from '../../supabase.service';
import { TesterService } from '../../tester.service';

class SubmitDto {
  @ApiProperty({ description: 'Base URL of the application to test' })
  base_url: string;

  @ApiProperty({ description: 'Name of the developer' })
  dev_name: string;

  @ApiProperty({ description: 'Project ID' })
  project_id: string;

  @ApiProperty({ description: 'API Key', required: false })
  api_key?: string;

  @ApiProperty({ description: 'Submission ID', required: false })
  submission_id?: string;

  @ApiProperty({ description: 'Started At timestamp', required: false })
  started_at?: string;
}

class VerifyDto {
  @ApiProperty({ description: 'Submission ID to verify' })
  submission_id: string;

  @ApiProperty({ description: 'Base URL of the application to test' })
  base_url: string;
}

class HealthResponse {
  @ApiProperty()
  status: string;

  @ApiProperty()
  service: string;

  @ApiProperty()
  timestamp: string;

  @ApiProperty()
  connections: {
    airtable: string;
    supabase: string;
  };
}

class SubmitResponse {
  @ApiProperty()
  status: string;

  @ApiProperty()
  submission_id: string;
}

class VerifyResponse {
  @ApiProperty()
  status: string;

  @ApiProperty()
  submission_id: string;

  @ApiProperty()
  test_status: string;

  @ApiProperty()
  score: number;

  @ApiProperty()
  token: string;

  @ApiProperty()
  logs_url: string;
}

class ResultResponse {
  @ApiProperty()
  status: string;

  @ApiProperty()
  submission_id: string;

  @ApiProperty()
  airtable_id: string;

  @ApiProperty()
  test_status: string;

  @ApiProperty()
  score: number;

  @ApiProperty()
  logs_url: string;
}

@ApiTags('Verifier')
@Controller('verifier')
export class VerifierController {
  constructor(
    private readonly airtableService: AirtableService,
    private readonly supabaseService: SupabaseService,
    private readonly testerService: TesterService,
  ) {}

  @Get('health')
  @ApiOperation({ summary: 'Check service health' })
  @ApiResponse({ status: 200, description: 'Service is healthy', type: HealthResponse })
  @ApiResponse({ status: 500, description: 'Service health check failed' })
  async healthCheck() {
    const airtableTest = await this.airtableService.testConnection();
    const supabaseTest = await this.supabaseService.testConnection();
    
    return {
      status: 'ok',
      service: 'Verifier',
      timestamp: new Date().toISOString(),
      connections: {
        airtable: airtableTest ? 'connected' : 'disconnected',
        supabase: supabaseTest ? 'connected' : 'disconnected'
      }
    };
  }

  @Post('submit')
  @ApiOperation({ summary: 'Submit a new verification request' })
  @ApiResponse({ status: 201, description: 'Submission created successfully', type: SubmitResponse })
  @ApiResponse({ status: 400, description: 'Invalid input' })
  @ApiResponse({ status: 500, description: 'Submission creation failed' })
  async submit(@Body() submitDto: SubmitDto) {
    const submissionId = await this.airtableService.createSubmission({
      "Project": submitDto.project_id,
      "Developer Name": submitDto.dev_name,
      "Base URL": submitDto.base_url,
      "Status": 'Pending',
      "Submission ID": submitDto.submission_id,
      "Started At": submitDto.started_at,
    });

    return {
      status: 'success',
      submission_id: submissionId
    };
  }

  @Post('verify')
  @ApiOperation({ summary: 'Verify a submission' })
  @ApiResponse({ status: 200, description: 'Verification completed', type: VerifyResponse })
  @ApiResponse({ status: 400, description: 'Invalid input' })
  @ApiResponse({ status: 500, description: 'Verification failed' })
  async verify(@Body() verifyDto: VerifyDto) {
    const result = await this.testerService.runChecks(verifyDto.base_url, {
      endpoints: [
        { path: '/health', expect: { status: 200 } },
        { path: '/register', method: 'POST', expect: { status: 200 } },
      ]
    });

    return {
      status: 'success',
      submission_id: verifyDto.submission_id,
      test_status: result.passed === result.total ? 'Pass' : 'Fail',
      score: (result.passed / result.total) * 100,
      token: 'generated-token',
      logs_url: await this.supabaseService.uploadJsonLog(verifyDto.submission_id, result)
    };
  }

  @Get('result/:id')
  @ApiOperation({ summary: 'Get verification result' })
  @ApiResponse({ status: 200, description: 'Result found', type: ResultResponse })
  @ApiResponse({ status: 404, description: 'Submission not found' })
  @ApiResponse({ status: 500, description: 'Error fetching result' })
  async getResult(@Param('id') id: string) {
    const submission = await this.airtableService.findSubmission(id);
    
    if (!submission) {
      throw new NotFoundException({
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
  }
}
