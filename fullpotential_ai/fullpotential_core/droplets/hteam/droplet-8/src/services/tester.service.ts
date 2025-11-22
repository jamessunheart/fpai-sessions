// src/services/tester.service.ts
import { Injectable } from '@nestjs/common';
import fetch from 'node-fetch';

@Injectable()
export class TesterService {
  async runChecks(baseUrl: string, assignment: any) {
  let passed = 0;
  const total = assignment.endpoints.length;
  const results: any[] = [];

  for (const ep of assignment.endpoints) {
    const url = baseUrl + ep.path;
    const method = ep.method || 'GET';
    const start = Date.now();

    try {
      const res = await fetch(url, { method });
      const latency = Date.now() - start;

      const success = res.status === ep.expect.status;
      if (success) passed++;

      results.push({
        endpoint: ep.path,
        expected_status: ep.expect.status,
        actual_status: res.status,
        latency_ms: latency,
        validation: success ? 'Pass' : 'Fail',
      });
    } catch (err: any) {
      results.push({
        endpoint: ep.path,
        expected_status: ep.expect.status,
        actual_status: 0,
        latency_ms: 0,
        validation: 'Fail',
        error: err.message,
      });
    }
  }

    return { passed, total, results };
  }
}
