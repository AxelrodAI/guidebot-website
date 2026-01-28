# Auto-Generated API Clients

Generate fully-typed Python and TypeScript API clients from OpenAPI specs, Swagger docs, or even cURL commands.

## Features

- **OpenAPI/Swagger Support** - Parse v2.0 and v3.0 specifications
- **cURL Parsing** - Convert cURL commands into typed clients
- **Multi-Language** - Generate Python (with type hints) or TypeScript (with fetch)
- **Authentication Ready** - Bearer token, API key, and basic auth support
- **Type Safe** - Full type annotations for IDE autocompletion
- **Error Handling** - Standard response wrapper with status codes
- **Visual Dashboard** - Browser-based generator with live preview

## Installation

No dependencies required for Python generation (Python 3.7+).

```bash
# For YAML support (optional)
pip install pyyaml

# Clone or download to your project
cd api-client-generator
```

## Quick Start

### From OpenAPI Spec

```bash
# Parse and inspect a spec
python api_generator.py parse petstore.json

# Generate Python client
python api_generator.py generate petstore.json -l python -o petstore_client.py

# Generate TypeScript client
python api_generator.py generate petstore.json -l typescript -o petstore_client.ts

# Preview code without saving
python api_generator.py preview petstore.json -l python
```

### From cURL Command

```bash
# Convert cURL to typed client
python api_generator.py from-curl 'curl -X GET "https://api.example.com/users" -H "Authorization: Bearer token123"'

# Save to file
python api_generator.py from-curl 'curl ...' -l python -o api_client.py
```

### From URL

```bash
# Load spec from URL
python api_generator.py parse https://api.example.com/openapi.json
python api_generator.py generate https://api.example.com/openapi.json -l python
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `parse` | Parse and inspect API spec | `parse petstore.json` |
| `generate` | Generate client code | `generate spec.json -l python -o client.py` |
| `preview` | Preview generated code | `preview spec.json -l typescript` |
| `validate` | Validate OpenAPI spec | `validate spec.json` |
| `from-curl` | Generate from cURL | `from-curl 'curl ...'` |
| `list-templates` | Show available templates | `list-templates` |

All commands support `--json` flag for machine-readable output.

## Generated Code Example

### Input (OpenAPI Spec)

```json
{
  "openapi": "3.0.0",
  "info": { "title": "User API", "version": "1.0.0" },
  "servers": [{ "url": "https://api.example.com" }],
  "components": {
    "securitySchemes": {
      "bearerAuth": { "type": "http", "scheme": "bearer" }
    }
  },
  "paths": {
    "/users/{userId}": {
      "get": {
        "operationId": "getUser",
        "summary": "Get user by ID",
        "parameters": [
          { "name": "userId", "in": "path", "required": true }
        ]
      }
    }
  }
}
```

### Output (Python)

```python
class UserApiClient:
    def __init__(
        self,
        base_url: str = "https://api.example.com",
        token: Optional[str] = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get_user(self, user_id: str) -> APIResponse:
        """
        Get user by ID
        GET /users/{userId}
        """
        path = f"/users/{user_id}"
        return self._request("GET", path)
```

### Output (TypeScript)

```typescript
export class UserApiClient {
  constructor(
    baseUrl: string = "https://api.example.com",
    token?: string
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.defaultHeaders = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async getUser(userId: string): Promise<APIResponse> {
    const path = `/users/${userId}`;
    return this.request("GET", path);
  }
}
```

## Dashboard

Open `index.html` in a browser for a visual interface:

- Paste OpenAPI specs or cURL commands
- Live preview of detected endpoints
- Generate Python or TypeScript with one click
- Try sample specs (Pet Store, GitHub, Weather APIs)

## Supported Authentication

| Type | Python | TypeScript |
|------|--------|------------|
| Bearer Token | ✅ | ✅ |
| API Key (header) | ✅ | ✅ |
| API Key (query) | ✅ | ✅ |
| Basic Auth | ✅ | ⚠️ partial |
| OAuth2 | ⚠️ header only | ⚠️ header only |

## File Structure

```
api-client-generator/
├── api_generator.py   # Main CLI tool
├── index.html         # Visual dashboard
├── README.md          # This file
├── data/              # Cached specs
├── templates/         # Code templates
└── output/            # Generated clients
```

## Tips

1. **Include operationId** - Makes method names more readable
2. **Add summaries** - Become docstrings in generated code
3. **Define security schemes** - Auto-configures auth in client
4. **Use path parameters** - Correctly typed in method signatures
5. **Specify types** - Better type inference in generated code

## Integration Examples

### Use Generated Python Client

```python
from my_api_client import MyApiClient

client = MyApiClient(
    base_url="https://api.example.com",
    token="your-bearer-token"
)

# Fully typed with IDE autocompletion!
response = client.get_user(user_id="123")

if response.success:
    print(response.data)
else:
    print(f"Error: {response.status_code}")
```

### Use Generated TypeScript Client

```typescript
import { MyApiClient } from './my_api_client';

const client = new MyApiClient(
  'https://api.example.com',
  'your-bearer-token'
);

const response = await client.getUser('123');

if (response.success) {
  console.log(response.data);
}
```

## Limitations

- Complex schema references may not resolve fully
- Nested request bodies simplified to `Dict[str, Any]`
- OAuth2 flows not fully supported (token management)
- Response types not generated (returns generic `Any`)

## Contributing

Part of the Guidebot feature pipeline. Improvements welcome!

## License

MIT
