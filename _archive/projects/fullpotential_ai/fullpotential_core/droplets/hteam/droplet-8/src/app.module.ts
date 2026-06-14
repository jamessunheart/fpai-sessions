import { Module } from '@nestjs/common';
import { AirtableService } from './services/airtable.service';
import { SupabaseService } from './services/supabase.service';
import { TesterService } from './services/tester.service';
import { VerifierService } from './services/modules/verifier/verifier.service';
import { VerifierController } from './services/modules/verifier/verifier.controller';

@Module({
  imports: [],
  controllers: [VerifierController],
  providers: [
    VerifierService,
    AirtableService,
    SupabaseService,
    TesterService,
  ],
})
export class AppModule {}

