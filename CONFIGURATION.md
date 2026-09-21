# Configuration

The system uses environment variables for runtime settings.

## Required keys

- `XAI_API_KEY`
- `XAI_BASE_URL`
- `XAI_MODEL`

## Example

See `.env.example` for the template.

## Safe practices

- never commit secrets
- configure environment-specific settings through the environment
- keep model/version settings separate from business logic
