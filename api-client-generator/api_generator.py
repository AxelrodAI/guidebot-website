#!/usr/bin/env python3
"""
Auto-Generated API Clients - Generate typed API wrappers from documentation.

Parse OpenAPI/Swagger specs or plain docs to generate fully-typed Python and
TypeScript API clients with authentication, error handling, and documentation.

Usage:
    python api_generator.py parse <spec_file_or_url>
    python api_generator.py generate <spec> --language <python|typescript>
    python api_generator.py preview <spec> [--endpoint <path>]
    python api_generator.py validate <spec>
    python api_generator.py list-templates
    python api_generator.py from-curl <curl_command>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs
import textwrap


# Data storage
DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent / "output"


@dataclass
class Parameter:
    """API parameter definition."""
    name: str
    location: str  # path, query, header, body
    type: str
    required: bool = False
    description: str = ""
    default: Any = None
    enum: List[str] = field(default_factory=list)


@dataclass
class Endpoint:
    """API endpoint definition."""
    method: str
    path: str
    operation_id: str
    summary: str = ""
    description: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[Dict] = None
    responses: Dict[str, Dict] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    auth_required: bool = False


@dataclass
class APISpec:
    """Complete API specification."""
    title: str
    version: str
    base_url: str
    description: str = ""
    endpoints: List[Endpoint] = field(default_factory=list)
    auth_type: str = ""  # bearer, api_key, basic, oauth2
    auth_location: str = ""  # header, query
    auth_name: str = ""


def ensure_dirs():
    """Create necessary directories."""
    DATA_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def parse_openapi(spec_data: Dict) -> APISpec:
    """Parse OpenAPI/Swagger specification."""
    info = spec_data.get('info', {})
    
    # Determine base URL
    base_url = ""
    if 'servers' in spec_data:
        base_url = spec_data['servers'][0].get('url', '')
    elif 'host' in spec_data:
        scheme = spec_data.get('schemes', ['https'])[0]
        base_path = spec_data.get('basePath', '')
        base_url = f"{scheme}://{spec_data['host']}{base_path}"
    
    # Parse security schemes
    auth_type = ""
    auth_location = ""
    auth_name = ""
    
    security_schemes = spec_data.get('components', {}).get('securitySchemes', {})
    if not security_schemes:
        security_schemes = spec_data.get('securityDefinitions', {})
    
    for name, scheme in security_schemes.items():
        scheme_type = scheme.get('type', '')
        if scheme_type == 'http' and scheme.get('scheme') == 'bearer':
            auth_type = 'bearer'
            auth_location = 'header'
            auth_name = 'Authorization'
        elif scheme_type in ['apiKey', 'api_key']:
            auth_type = 'api_key'
            auth_location = scheme.get('in', 'header')
            auth_name = scheme.get('name', 'X-API-Key')
        elif scheme_type == 'basic':
            auth_type = 'basic'
            auth_location = 'header'
            auth_name = 'Authorization'
        elif scheme_type == 'oauth2':
            auth_type = 'oauth2'
            auth_location = 'header'
            auth_name = 'Authorization'
    
    # Parse endpoints
    endpoints = []
    paths = spec_data.get('paths', {})
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                endpoint = parse_endpoint(method, path, operation, spec_data)
                endpoints.append(endpoint)
    
    return APISpec(
        title=info.get('title', 'API'),
        version=info.get('version', '1.0.0'),
        base_url=base_url,
        description=info.get('description', ''),
        endpoints=endpoints,
        auth_type=auth_type,
        auth_location=auth_location,
        auth_name=auth_name
    )


def parse_endpoint(method: str, path: str, operation: Dict, spec: Dict) -> Endpoint:
    """Parse a single endpoint definition."""
    operation_id = operation.get('operationId', '')
    if not operation_id:
        # Generate operation ID from method and path
        clean_path = re.sub(r'[{}]', '', path).replace('/', '_').strip('_')
        operation_id = f"{method}_{clean_path}"
    
    parameters = []
    
    # Parse parameters
    for param in operation.get('parameters', []):
        parameters.append(Parameter(
            name=param.get('name', ''),
            location=param.get('in', 'query'),
            type=resolve_type(param.get('schema', param), spec),
            required=param.get('required', False),
            description=param.get('description', ''),
            default=param.get('default'),
            enum=param.get('enum', param.get('schema', {}).get('enum', []))
        ))
    
    # Parse request body
    request_body = None
    if 'requestBody' in operation:
        rb = operation['requestBody']
        content = rb.get('content', {})
        for content_type, schema_info in content.items():
            request_body = {
                'content_type': content_type,
                'schema': resolve_schema(schema_info.get('schema', {}), spec),
                'required': rb.get('required', False)
            }
            break
    
    # Parse responses
    responses = {}
    for code, response in operation.get('responses', {}).items():
        content = response.get('content', {})
        schema = None
        for ct, info in content.items():
            schema = resolve_schema(info.get('schema', {}), spec)
            break
        responses[code] = {
            'description': response.get('description', ''),
            'schema': schema
        }
    
    # Check if auth required
    auth_required = bool(operation.get('security', spec.get('security', [])))
    
    return Endpoint(
        method=method.upper(),
        path=path,
        operation_id=operation_id,
        summary=operation.get('summary', ''),
        description=operation.get('description', ''),
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        tags=operation.get('tags', []),
        auth_required=auth_required
    )


def resolve_type(schema: Dict, spec: Dict) -> str:
    """Resolve schema to a type string."""
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')[-1]
        return ref_path
    
    schema_type = schema.get('type', 'any')
    
    if schema_type == 'array':
        items_type = resolve_type(schema.get('items', {}), spec)
        return f"List[{items_type}]"
    elif schema_type == 'object':
        return 'Dict[str, Any]'
    elif schema_type == 'integer':
        return 'int'
    elif schema_type == 'number':
        return 'float'
    elif schema_type == 'boolean':
        return 'bool'
    elif schema_type == 'string':
        fmt = schema.get('format', '')
        if fmt == 'date-time':
            return 'datetime'
        elif fmt == 'date':
            return 'date'
        return 'str'
    
    return 'Any'


def resolve_schema(schema: Dict, spec: Dict) -> Dict:
    """Resolve $ref and return full schema."""
    if '$ref' in schema:
        ref_path = schema['$ref']
        parts = ref_path.split('/')
        
        # Navigate to the referenced schema
        result = spec
        for part in parts:
            if part == '#':
                continue
            result = result.get(part, {})
        return result
    return schema


def parse_curl(curl_command: str) -> APISpec:
    """Parse a cURL command into an API spec."""
    # Clean up the command
    curl_command = curl_command.replace('\\\n', ' ').strip()
    
    # Extract URL
    url_match = re.search(r"curl\s+(?:.*?\s+)?['\"]?(https?://[^\s'\"]+)['\"]?", curl_command)
    if not url_match:
        url_match = re.search(r"(https?://[^\s'\"]+)", curl_command)
    
    url = url_match.group(1) if url_match else ""
    parsed = urlparse(url)
    
    # Extract method
    method = 'GET'
    method_match = re.search(r'-X\s+(\w+)', curl_command)
    if method_match:
        method = method_match.group(1).upper()
    elif '-d' in curl_command or '--data' in curl_command:
        method = 'POST'
    
    # Extract headers
    headers = []
    header_matches = re.findall(r"-H\s+['\"]([^'\"]+)['\"]", curl_command)
    auth_type = ""
    auth_name = ""
    
    for header in header_matches:
        if ':' in header:
            name, value = header.split(':', 1)
            name = name.strip()
            value = value.strip()
            
            if name.lower() == 'authorization':
                if value.lower().startswith('bearer'):
                    auth_type = 'bearer'
                    auth_name = 'Authorization'
                elif value.lower().startswith('basic'):
                    auth_type = 'basic'
                    auth_name = 'Authorization'
            elif name.lower() in ['x-api-key', 'api-key', 'apikey']:
                auth_type = 'api_key'
                auth_name = name
            else:
                headers.append(Parameter(
                    name=name,
                    location='header',
                    type='str',
                    required=True
                ))
    
    # Extract path parameters
    path = parsed.path
    path_params = re.findall(r'/(\d+)(?=/|$)', path)
    for i, param in enumerate(path_params):
        path = path.replace(f'/{param}', f'/{{id{i+1}}}')
    
    # Extract query parameters
    query_params = []
    if parsed.query:
        for key, values in parse_qs(parsed.query).items():
            query_params.append(Parameter(
                name=key,
                location='query',
                type='str',
                required=False,
                default=values[0] if values else None
            ))
    
    # Extract body data
    request_body = None
    data_match = re.search(r"(?:-d|--data)\s+['\"]([^'\"]+)['\"]", curl_command)
    if data_match:
        try:
            body_data = json.loads(data_match.group(1))
            request_body = {
                'content_type': 'application/json',
                'schema': {'type': 'object', 'properties': {k: {'type': infer_type(v)} for k, v in body_data.items()}},
                'required': True
            }
        except json.JSONDecodeError:
            request_body = {
                'content_type': 'application/x-www-form-urlencoded',
                'schema': {'type': 'object'},
                'required': True
            }
    
    # Build parameters list
    parameters = headers + query_params
    for i, param in enumerate(path_params):
        parameters.append(Parameter(
            name=f'id{i+1}',
            location='path',
            type='str',
            required=True
        ))
    
    endpoint = Endpoint(
        method=method,
        path=path,
        operation_id=f"{method.lower()}_{path.replace('/', '_').strip('_')}",
        parameters=parameters,
        request_body=request_body,
        auth_required=bool(auth_type)
    )
    
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    return APISpec(
        title='Parsed API',
        version='1.0.0',
        base_url=base_url,
        endpoints=[endpoint],
        auth_type=auth_type,
        auth_location='header',
        auth_name=auth_name
    )


def infer_type(value: Any) -> str:
    """Infer JSON schema type from value."""
    if isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, int):
        return 'integer'
    elif isinstance(value, float):
        return 'number'
    elif isinstance(value, list):
        return 'array'
    elif isinstance(value, dict):
        return 'object'
    return 'string'


def generate_python_client(spec: APISpec) -> str:
    """Generate Python client code."""
    lines = [
        '"""',
        f'{spec.title} API Client',
        f'Version: {spec.version}',
        '',
        spec.description[:200] if spec.description else 'Auto-generated API client.',
        '"""',
        '',
        'import requests',
        'from typing import Optional, List, Dict, Any, Union',
        'from dataclasses import dataclass',
        'from datetime import datetime, date',
        '',
        '',
        '@dataclass',
        'class APIResponse:',
        '    """Standard API response wrapper."""',
        '    status_code: int',
        '    data: Any',
        '    headers: Dict[str, str]',
        '    success: bool',
        '',
        '    @property',
        '    def json(self) -> Any:',
        '        return self.data',
        '',
        '',
        f'class {to_class_name(spec.title)}Client:',
        f'    """',
        f'    {spec.title} API Client',
        f'    ',
        f'    Base URL: {spec.base_url}',
        f'    """',
        '',
        '    def __init__(',
        '        self,',
        f'        base_url: str = "{spec.base_url}",',
    ]
    
    # Add auth parameter based on type
    if spec.auth_type == 'bearer':
        lines.append('        token: Optional[str] = None,')
    elif spec.auth_type == 'api_key':
        lines.append('        api_key: Optional[str] = None,')
    elif spec.auth_type == 'basic':
        lines.append('        username: Optional[str] = None,')
        lines.append('        password: Optional[str] = None,')
    
    lines.extend([
        '        timeout: int = 30',
        '    ):',
        '        self.base_url = base_url.rstrip("/")',
        '        self.timeout = timeout',
        '        self.session = requests.Session()',
    ])
    
    # Set up auth
    if spec.auth_type == 'bearer':
        lines.extend([
            '        if token:',
            '            self.session.headers["Authorization"] = f"Bearer {token}"',
        ])
    elif spec.auth_type == 'api_key':
        lines.extend([
            '        if api_key:',
            f'            self.session.headers["{spec.auth_name}"] = api_key',
        ])
    elif spec.auth_type == 'basic':
        lines.extend([
            '        if username and password:',
            '            self.session.auth = (username, password)',
        ])
    
    lines.extend([
        '',
        '    def _request(',
        '        self,',
        '        method: str,',
        '        path: str,',
        '        params: Optional[Dict] = None,',
        '        json_data: Optional[Dict] = None,',
        '        headers: Optional[Dict] = None',
        '    ) -> APIResponse:',
        '        """Make an API request."""',
        '        url = f"{self.base_url}{path}"',
        '        ',
        '        response = self.session.request(',
        '            method=method,',
        '            url=url,',
        '            params=params,',
        '            json=json_data,',
        '            headers=headers,',
        '            timeout=self.timeout',
        '        )',
        '        ',
        '        try:',
        '            data = response.json()',
        '        except ValueError:',
        '            data = response.text',
        '        ',
        '        return APIResponse(',
        '            status_code=response.status_code,',
        '            data=data,',
        '            headers=dict(response.headers),',
        '            success=response.ok',
        '        )',
        '',
    ])
    
    # Generate method for each endpoint
    for endpoint in spec.endpoints:
        lines.extend(generate_python_method(endpoint))
    
    # Add example usage
    lines.extend([
        '',
        '',
        '# Example usage:',
        '# ',
        f'# client = {to_class_name(spec.title)}Client(',
    ])
    
    if spec.auth_type == 'bearer':
        lines.append('#     token="your-token-here"')
    elif spec.auth_type == 'api_key':
        lines.append('#     api_key="your-api-key-here"')
    
    lines.append('# )')
    
    if spec.endpoints:
        ep = spec.endpoints[0]
        lines.append(f'# response = client.{to_method_name(ep.operation_id)}(...)')
        lines.append('# print(response.json)')
    
    return '\n'.join(lines)


def generate_python_method(endpoint: Endpoint) -> List[str]:
    """Generate Python method for an endpoint."""
    method_name = to_method_name(endpoint.operation_id)
    
    # Build parameter list
    params = []
    path_params = []
    query_params = []
    header_params = []
    
    for param in endpoint.parameters:
        py_type = to_python_type(param.type)
        if not param.required:
            py_type = f"Optional[{py_type}]"
        
        if param.location == 'path':
            params.append(f'{to_snake_case(param.name)}: {py_type}')
            path_params.append(param)
        elif param.location == 'query':
            default = f' = {repr(param.default)}' if param.default is not None else ' = None'
            if param.required:
                params.append(f'{to_snake_case(param.name)}: {py_type}')
            else:
                params.append(f'{to_snake_case(param.name)}: {py_type}{default}')
            query_params.append(param)
        elif param.location == 'header':
            header_params.append(param)
    
    # Add body parameter
    if endpoint.request_body:
        params.append('body: Dict[str, Any]')
    
    # Build method signature
    lines = [
        f'    def {method_name}(',
        '        self,',
    ]
    
    for param in params:
        lines.append(f'        {param},')
    
    lines.append('    ) -> APIResponse:')
    
    # Docstring
    lines.append('        """')
    lines.append(f'        {endpoint.summary or endpoint.operation_id}')
    if endpoint.description:
        lines.append(f'        ')
        lines.append(f'        {endpoint.description[:150]}')
    lines.append(f'        ')
    lines.append(f'        {endpoint.method} {endpoint.path}')
    
    if endpoint.parameters:
        lines.append('        ')
        lines.append('        Args:')
        for param in endpoint.parameters:
            lines.append(f'            {to_snake_case(param.name)}: {param.description or param.name}')
    
    if endpoint.request_body:
        lines.append('            body: Request body')
    
    lines.append('        ')
    lines.append('        Returns:')
    lines.append('            APIResponse with status_code, data, headers, success')
    lines.append('        """')
    
    # Build path with parameters
    path = endpoint.path
    for param in path_params:
        path = path.replace(f'{{{param.name}}}', f'{{{to_snake_case(param.name)}}}')
    
    lines.append(f'        path = f"{path}"')
    
    # Build query params
    if query_params:
        lines.append('        params = {}')
        for param in query_params:
            snake_name = to_snake_case(param.name)
            lines.append(f'        if {snake_name} is not None:')
            lines.append(f'            params["{param.name}"] = {snake_name}')
    else:
        lines.append('        params = None')
    
    # Build headers
    if header_params:
        lines.append('        headers = {}')
        for param in header_params:
            snake_name = to_snake_case(param.name)
            lines.append(f'        headers["{param.name}"] = {snake_name}')
    else:
        lines.append('        headers = None')
    
    # Body
    body_arg = 'body' if endpoint.request_body else 'None'
    
    # Make request
    lines.append(f'        return self._request("{endpoint.method}", path, params=params, json_data={body_arg}, headers=headers)')
    lines.append('')
    
    return lines


def generate_typescript_client(spec: APISpec) -> str:
    """Generate TypeScript client code."""
    lines = [
        '/**',
        f' * {spec.title} API Client',
        f' * Version: {spec.version}',
        ' * ',
        f' * {spec.description[:100] if spec.description else "Auto-generated API client."}',
        ' */',
        '',
        'interface APIResponse<T = any> {',
        '  statusCode: number;',
        '  data: T;',
        '  headers: Record<string, string>;',
        '  success: boolean;',
        '}',
        '',
        'interface RequestOptions {',
        '  params?: Record<string, any>;',
        '  body?: any;',
        '  headers?: Record<string, string>;',
        '}',
        '',
        f'export class {to_class_name(spec.title)}Client {{',
        '  private baseUrl: string;',
        '  private defaultHeaders: Record<string, string>;',
        '',
        '  constructor(',
        f'    baseUrl: string = "{spec.base_url}",',
    ]
    
    if spec.auth_type == 'bearer':
        lines.append('    token?: string,')
    elif spec.auth_type == 'api_key':
        lines.append('    apiKey?: string,')
    
    lines.extend([
        '  ) {',
        '    this.baseUrl = baseUrl.replace(/\\/$/, "");',
        '    this.defaultHeaders = {',
        '      "Content-Type": "application/json",',
    ])
    
    if spec.auth_type == 'bearer':
        lines.append('      ...(token ? { Authorization: `Bearer ${token}` } : {}),')
    elif spec.auth_type == 'api_key':
        lines.append(f'      ...(apiKey ? {{ "{spec.auth_name}": apiKey }} : {{}}),')
    
    lines.extend([
        '    };',
        '  }',
        '',
        '  private async request<T>(',
        '    method: string,',
        '    path: string,',
        '    options: RequestOptions = {}',
        '  ): Promise<APIResponse<T>> {',
        '    const url = new URL(`${this.baseUrl}${path}`);',
        '    ',
        '    if (options.params) {',
        '      Object.entries(options.params).forEach(([key, value]) => {',
        '        if (value !== undefined && value !== null) {',
        '          url.searchParams.append(key, String(value));',
        '        }',
        '      });',
        '    }',
        '',
        '    const response = await fetch(url.toString(), {',
        '      method,',
        '      headers: { ...this.defaultHeaders, ...options.headers },',
        '      body: options.body ? JSON.stringify(options.body) : undefined,',
        '    });',
        '',
        '    let data: T;',
        '    try {',
        '      data = await response.json();',
        '    } catch {',
        '      data = await response.text() as any;',
        '    }',
        '',
        '    return {',
        '      statusCode: response.status,',
        '      data,',
        '      headers: Object.fromEntries(response.headers.entries()),',
        '      success: response.ok,',
        '    };',
        '  }',
        '',
    ])
    
    # Generate methods
    for endpoint in spec.endpoints:
        lines.extend(generate_typescript_method(endpoint))
    
    lines.append('}')
    
    # Example usage
    lines.extend([
        '',
        '// Example usage:',
        '// ',
        f'// const client = new {to_class_name(spec.title)}Client(',
        f'//   "{spec.base_url}",',
    ])
    
    if spec.auth_type == 'bearer':
        lines.append('//   "your-token-here"')
    elif spec.auth_type == 'api_key':
        lines.append('//   "your-api-key-here"')
    
    lines.append('// );')
    
    if spec.endpoints:
        ep = spec.endpoints[0]
        lines.append(f'// const response = await client.{to_camel_case(ep.operation_id)}(...);')
        lines.append('// console.log(response.data);')
    
    return '\n'.join(lines)


def generate_typescript_method(endpoint: Endpoint) -> List[str]:
    """Generate TypeScript method for an endpoint."""
    method_name = to_camel_case(endpoint.operation_id)
    
    # Build parameters
    params = []
    path_params = []
    query_params = []
    
    for param in endpoint.parameters:
        ts_type = to_typescript_type(param.type)
        optional = '' if param.required else '?'
        
        if param.location == 'path':
            params.append(f'{to_camel_case(param.name)}: {ts_type}')
            path_params.append(param)
        elif param.location == 'query':
            params.append(f'{to_camel_case(param.name)}{optional}: {ts_type}')
            query_params.append(param)
    
    if endpoint.request_body:
        params.append('body: Record<string, any>')
    
    lines = [
        '  /**',
        f'   * {endpoint.summary or endpoint.operation_id}',
        f'   * {endpoint.method} {endpoint.path}',
        '   */',
        f'  async {method_name}(',
    ]
    
    for param in params:
        lines.append(f'    {param},')
    
    lines.append('  ): Promise<APIResponse> {')
    
    # Build path
    path = endpoint.path
    for param in path_params:
        path = path.replace(f'{{{param.name}}}', f'${{{to_camel_case(param.name)}}}')
    
    lines.append(f'    const path = `{path}`;')
    
    # Build params object
    if query_params:
        lines.append('    const params: Record<string, any> = {};')
        for param in query_params:
            camel_name = to_camel_case(param.name)
            lines.append(f'    if ({camel_name} !== undefined) params["{param.name}"] = {camel_name};')
    
    # Make request
    request_options = []
    if query_params:
        request_options.append('params')
    if endpoint.request_body:
        request_options.append('body')
    
    opts = ', '.join(request_options)
    if opts:
        opts = f'{{ {opts} }}'
    else:
        opts = '{}'
    
    lines.append(f'    return this.request("{endpoint.method}", path, {opts});')
    lines.append('  }')
    lines.append('')
    
    return lines


def to_class_name(name: str) -> str:
    """Convert to PascalCase class name."""
    # Remove special characters and split
    words = re.split(r'[\s\-_]+', name)
    return ''.join(word.capitalize() for word in words if word)


def to_method_name(name: str) -> str:
    """Convert to snake_case method name."""
    return to_snake_case(name)


def to_snake_case(name: str) -> str:
    """Convert to snake_case."""
    # Handle camelCase
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return re.sub(r'[\s\-]+', '_', s2).lower()


def to_camel_case(name: str) -> str:
    """Convert to camelCase."""
    words = re.split(r'[\s\-_]+', name)
    if not words:
        return name
    return words[0].lower() + ''.join(w.capitalize() for w in words[1:])


def to_python_type(schema_type: str) -> str:
    """Convert schema type to Python type."""
    mapping = {
        'string': 'str',
        'integer': 'int',
        'number': 'float',
        'boolean': 'bool',
        'array': 'List',
        'object': 'Dict[str, Any]',
        'any': 'Any',
    }
    return mapping.get(schema_type, schema_type)


def to_typescript_type(schema_type: str) -> str:
    """Convert schema type to TypeScript type."""
    mapping = {
        'string': 'string',
        'integer': 'number',
        'number': 'number',
        'boolean': 'boolean',
        'array': 'any[]',
        'object': 'Record<string, any>',
        'any': 'any',
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
    }
    return mapping.get(schema_type, 'any')


def load_spec(source: str) -> Dict:
    """Load spec from file or URL."""
    if source.startswith(('http://', 'https://')):
        import urllib.request
        with urllib.request.urlopen(source) as response:
            content = response.read().decode('utf-8')
    else:
        content = Path(source).read_text(encoding='utf-8')
    
    if source.endswith(('.yaml', '.yml')):
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            print("Warning: PyYAML not installed, trying as JSON")
    
    return json.loads(content)


def validate_spec(spec_data: Dict) -> Dict:
    """Validate an OpenAPI spec."""
    issues = []
    warnings = []
    
    # Check required fields
    if 'info' not in spec_data:
        issues.append("Missing 'info' section")
    else:
        if 'title' not in spec_data['info']:
            issues.append("Missing 'info.title'")
        if 'version' not in spec_data['info']:
            warnings.append("Missing 'info.version'")
    
    if 'paths' not in spec_data:
        issues.append("Missing 'paths' section")
    else:
        for path, methods in spec_data['paths'].items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    if 'responses' not in operation:
                        warnings.append(f"No responses defined for {method.upper()} {path}")
                    if 'operationId' not in operation:
                        warnings.append(f"No operationId for {method.upper()} {path}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'endpoints': len(spec_data.get('paths', {}))
    }


def format_output(data: Dict, as_json: bool = False) -> str:
    """Format output for display."""
    if as_json:
        return json.dumps(data, indent=2)
    
    if 'error' in data:
        return f"❌ Error: {data['error']}"
    
    lines = []
    
    if 'code' in data:
        return data['code']
    
    if 'valid' in data:
        lines.append("📋 VALIDATION RESULTS")
        lines.append(f"   Status: {'✅ Valid' if data['valid'] else '❌ Invalid'}")
        lines.append(f"   Endpoints: {data['endpoints']}")
        
        if data['issues']:
            lines.append("\n   Issues:")
            for issue in data['issues']:
                lines.append(f"      ❌ {issue}")
        
        if data['warnings']:
            lines.append("\n   Warnings:")
            for warn in data['warnings']:
                lines.append(f"      ⚠️ {warn}")
    
    elif 'title' in data and 'endpoints' in data:
        lines.append(f"📡 API SPECIFICATION: {data['title']}")
        lines.append(f"   Version: {data['version']}")
        lines.append(f"   Base URL: {data['base_url']}")
        lines.append(f"   Auth: {data.get('auth_type', 'none') or 'none'}")
        lines.append(f"   Endpoints: {len(data['endpoints'])}")
        
        for ep in data['endpoints'][:10]:
            auth_badge = '🔒' if ep.get('auth_required') else '🔓'
            lines.append(f"\n   {auth_badge} {ep['method']} {ep['path']}")
            if ep.get('summary'):
                lines.append(f"      {ep['summary'][:60]}")
    
    elif 'generated' in data:
        lines.append(f"✅ GENERATED: {data['output_file']}")
        lines.append(f"   Language: {data['language']}")
        lines.append(f"   Size: {data['size']} bytes")
        lines.append(f"   Methods: {data['methods']}")
    
    return '\n'.join(lines) if lines else json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Auto-Generated API Clients - Generate typed wrappers from API docs'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # parse command
    parse_parser = subparsers.add_parser('parse', help='Parse API spec')
    parse_parser.add_argument('spec', help='OpenAPI spec file or URL')
    parse_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # generate command
    gen_parser = subparsers.add_parser('generate', help='Generate client code')
    gen_parser.add_argument('spec', help='OpenAPI spec file or URL')
    gen_parser.add_argument('--language', '-l', choices=['python', 'typescript'], default='python')
    gen_parser.add_argument('--output', '-o', help='Output file')
    gen_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # preview command
    preview_parser = subparsers.add_parser('preview', help='Preview generated code')
    preview_parser.add_argument('spec', help='OpenAPI spec file or URL')
    preview_parser.add_argument('--language', '-l', choices=['python', 'typescript'], default='python')
    preview_parser.add_argument('--endpoint', help='Filter to specific endpoint path')
    
    # validate command
    validate_parser = subparsers.add_parser('validate', help='Validate API spec')
    validate_parser.add_argument('spec', help='OpenAPI spec file or URL')
    validate_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # from-curl command
    curl_parser = subparsers.add_parser('from-curl', help='Generate from cURL command')
    curl_parser.add_argument('curl', help='cURL command string')
    curl_parser.add_argument('--language', '-l', choices=['python', 'typescript'], default='python')
    curl_parser.add_argument('--output', '-o', help='Output file')
    
    # list-templates command
    subparsers.add_parser('list-templates', help='List available templates')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    ensure_dirs()
    
    result = {}
    as_json = getattr(args, 'json', False)
    
    try:
        if args.command == 'parse':
            spec_data = load_spec(args.spec)
            api_spec = parse_openapi(spec_data)
            result = {
                'title': api_spec.title,
                'version': api_spec.version,
                'base_url': api_spec.base_url,
                'auth_type': api_spec.auth_type,
                'endpoints': [
                    {
                        'method': ep.method,
                        'path': ep.path,
                        'operation_id': ep.operation_id,
                        'summary': ep.summary,
                        'auth_required': ep.auth_required,
                        'parameters': len(ep.parameters)
                    }
                    for ep in api_spec.endpoints
                ]
            }
        
        elif args.command == 'generate':
            spec_data = load_spec(args.spec)
            api_spec = parse_openapi(spec_data)
            
            if args.language == 'python':
                code = generate_python_client(api_spec)
                ext = 'py'
            else:
                code = generate_typescript_client(api_spec)
                ext = 'ts'
            
            output_file = args.output or (OUTPUT_DIR / f"{to_snake_case(api_spec.title)}_client.{ext}")
            output_path = Path(output_file)
            output_path.write_text(code, encoding='utf-8')
            
            result = {
                'generated': True,
                'output_file': str(output_path),
                'language': args.language,
                'size': len(code),
                'methods': len(api_spec.endpoints)
            }
        
        elif args.command == 'preview':
            spec_data = load_spec(args.spec)
            api_spec = parse_openapi(spec_data)
            
            if args.endpoint:
                api_spec.endpoints = [ep for ep in api_spec.endpoints if args.endpoint in ep.path]
            
            if args.language == 'python':
                code = generate_python_client(api_spec)
            else:
                code = generate_typescript_client(api_spec)
            
            result = {'code': code}
        
        elif args.command == 'validate':
            spec_data = load_spec(args.spec)
            result = validate_spec(spec_data)
        
        elif args.command == 'from-curl':
            api_spec = parse_curl(args.curl)
            
            if args.language == 'python':
                code = generate_python_client(api_spec)
                ext = 'py'
            else:
                code = generate_typescript_client(api_spec)
                ext = 'ts'
            
            if args.output:
                Path(args.output).write_text(code, encoding='utf-8')
                result = {'generated': True, 'output_file': args.output, 'language': args.language}
            else:
                result = {'code': code}
        
        elif args.command == 'list-templates':
            result = {
                'templates': [
                    {'name': 'python', 'description': 'Python client with type hints and requests'},
                    {'name': 'typescript', 'description': 'TypeScript client with fetch API'}
                ]
            }
    
    except Exception as e:
        result = {'error': str(e)}
    
    print(format_output(result, as_json))


if __name__ == '__main__':
    main()
