# daikon-chemvault

## Configuration

The application loads configuration from environment variables (or a local `.env` file) using structured Pydantic settings. Nested fields use a double-underscore delimiter (for example, `DATABASE__URL`), and several top-level aliases are supported for convenience.

### Key environment variables

| Variable | Description | Default |
| --- | --- | --- |
| `APP__NAME` | Display name for logs and diagnostics. | `ChemVault` |
| `APP__ENVIRONMENT` | Deployment environment indicator. | `production` |
| `APP__RDKIT_ENABLED` | Toggle RDKit-powered functionality. | `true` |
| `APP__RDKIT_PAINS_FILTER_ENABLED` | Toggle RDKit PAINS filtering. | `true` |
| `DATABASE__URL` / `DATABASE_URL` | Async database URL. | `postgresql+asyncpg://postgres:postgres@localhost:5432/chemvault` |
| `DATABASE__POOL_SIZE` / `DATABASE_POOL_SIZE` | Core connection pool size. | `10` |
| `DATABASE__MAX_OVERFLOW` / `DATABASE_MAX_OVERFLOW` | Extra connections allowed beyond the pool. | `20` |
| `DATABASE__POOL_TIMEOUT` / `DATABASE_POOL_TIMEOUT` | Seconds to wait for a connection before timing out. | `30` |
| `DATABASE__POOL_RECYCLE` / `DATABASE_POOL_RECYCLE` | Seconds before recycling connections. | `1800` |
| `DATABASE__ECHO` / `DATABASE_ECHO` | Enable SQLAlchemy engine echo for debugging. | `false` |
| `LOGGING__LEVEL` / `LOG_LEVEL` | Minimum log level. | `INFO` |
| `LOGGING__JSON` / `LOG_JSON` | Emit logs in JSON format. | `false` |
| `LOGGING__ROTATION` | File rotation threshold for log files. | `10 MB` |
| `LOGGING__RETENTION` | Retention period for log files. | `10 days` |
| `LOGGING__DIRECTORY` | Relative path for application logs. | `var/logs` |
| `SECURITY__ALLOWED_HOSTS` / `ALLOWED_HOSTS` | Comma-separated allowlist of hosts. | _empty_ |
| `SECURITY__CORS_ORIGINS` / `CORS_ORIGINS` | Comma-separated list of CORS origins. | _empty_ |

### Example `.env`

```env
APP__ENVIRONMENT=production
APP__RDKIT_ENABLED=true
DATABASE__URL=postgresql+asyncpg://postgres:postgres@db:5432/chemvault
DATABASE__POOL_SIZE=15
DATABASE__POOL_TIMEOUT=45
LOGGING__LEVEL=INFO
LOGGING__JSON=false
SECURITY__CORS_ORIGINS=https://example.com,https://admin.example.com
```
