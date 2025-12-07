# daikon-chemvault

## Running in Codex

For local development inside the Codex environment, use the dedicated compose stack that bundles the API and PostgreSQL database.

1. Copy the sample environment and adjust values if needed:
   ```bash
   cp .env.codex.example .env.codex
   ```
2. Start the stack:
   ```bash
   docker-compose -f docker-compose.codex.yml up --build
   ```

The API is exposed on port `10001`, and the database is reachable at `daikon_chem_vault_db:5432` using the credentials in `.env.codex`.

The existing compose files remain unchanged for production usage.
