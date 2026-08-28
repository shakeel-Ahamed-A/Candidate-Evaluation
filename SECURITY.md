# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a suspected security vulnerability. Contact the repository maintainer privately with reproduction details and affected files.

## Secrets

Never commit `.env`, API keys, access tokens, passwords, candidate private data, or production credentials. Use `.env.example` as the configuration template.

## Candidate data

Candidate resumes and transcripts are sensitive hiring data. Use synthetic or consented data for development and demos, apply least-privilege access controls, and avoid sending unnecessary personal information to external model providers.
