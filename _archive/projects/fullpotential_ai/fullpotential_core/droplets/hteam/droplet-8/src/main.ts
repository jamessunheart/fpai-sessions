// src/main.ts
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, NestFastifyApplication } from '@nestjs/platform-fastify';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { env } from './config/env';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({
      trustProxy: true
    })
  );

  // Enable CORS
  app.enableCors();

  // Setup Swagger documentation
  const config = new DocumentBuilder()
    .setTitle('Verifier API')
    .setDescription('The Verifier API documentation')
    .setVersion('1.0')
    .addTag('verifier')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document);

  // Start server
  const port = Number(env.PORT) || 8090;
  const host = '0.0.0.0';
  
  try {
    await app.listen({
      port: port,
      host: host
    });
    console.log(`✅ Verifier running at http://${host}:${port}`);
    console.log(`📚 Swagger documentation available at http://${host}:${port}/docs`);
    
    // Get the actual address the server is listening on
    const serverUrl = await app.getUrl();
    console.log(`🌐 Server URL: ${serverUrl}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

bootstrap().catch((err) => {
  console.error('❌ Server start failed:', err);
  process.exit(1);
});
