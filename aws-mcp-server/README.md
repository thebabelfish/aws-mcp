# AWS MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to execute AWS CLI commands with profile and region awareness.

## Features

- **Profile & Region Aware**: Automatically discovers AWS profiles from `~/.aws/config`
- **Enforced Permission Model**: Separate tools for read vs write operations force AI clients to request permission appropriately
- **Smart Command Classification**: Extensive list of read-only command prefixes for common AWS operations
- **Error Handling**: Graceful handling of timeouts, errors, and invalid commands
- **MCP Compatible**: Works with any MCP-compatible AI assistant (Claude, Copilot, etc.)

## Installation

1. Clone the repository:
```bash
cd aws-mcp-server
```

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

#### Option 1: MCP stdio Server (for Claude Desktop)
```bash
python aws_mcp_server.py
```

#### Option 2: HTTP Server (for VS Code Copilot and HTTP MCP clients)
```bash
python aws_mcp_http_server.py --port 8000
```

The stdio server communicates via stdin/stdout for MCP clients. The HTTP server provides MCP over HTTP transport with SSE endpoints.

### Available Tools

1. **execute_aws_read_command**
   - Execute read-only AWS CLI commands (describe, list, get, show, etc.)
   - Never requires user approval
   - Parameters:
     - `command` (required): The AWS command to execute (without 'aws' prefix)
     - `profile` (optional): AWS profile to use
     - `region` (optional): AWS region to override

2. **execute_aws_write_command**
   - Execute write AWS CLI commands (create, delete, update, modify, etc.)
   - Always requires user approval from the AI client
   - Parameters:
     - `command` (required): The AWS command to execute (without 'aws' prefix)
     - `profile` (optional): AWS profile to use
     - `region` (optional): AWS region to override

3. **list_aws_profiles**
   - List all available AWS profiles from `~/.aws/config`
   - No parameters required

### Example Commands

#### MCP Client (Claude Desktop)
```json
// List S3 buckets (read-only, no approval needed)
{
  "tool": "execute_aws_read_command",
  "arguments": {
    "command": "s3 ls",
    "profile": "production"
  }
}

// Create S3 bucket (write operation, requires approval)
{
  "tool": "execute_aws_write_command", 
  "arguments": {
    "command": "s3 mb s3://my-new-bucket",
    "profile": "dev",
    "region": "us-west-2"
  }
}
```

#### HTTP MCP Client (VS Code Copilot, custom integrations)
The HTTP server provides multiple transport options:

**Direct MCP (Recommended for VS Code Copilot):**
- **POST to root**: `POST http://localhost:8000/` with MCP JSON-RPC payload

**Alternative transports:**
- **Streamable HTTP**: `POST http://localhost:8000/mcp`
- **SSE**: `GET http://localhost:8000/sse-transport/sse` + `POST http://localhost:8000/sse-transport/messages`

Example MCP requests:
```bash
# List tools
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Call read tool
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "execute_aws_read_command", "arguments": {"command": "s3 ls"}}, "id": 2}'
```

## Security

- **Enforced Permission Model**: Separate tools for read vs write operations force proper AI client behavior
- **No Server-Side Permissions**: All permission control is handled by the AI client
- **Command Classification**: Smart detection of read-only vs write operations with validation
- **Local Only**: Designed to run locally with your AWS credentials
- **Profile Isolation**: Operations are scoped to the specified AWS profile

## Read-Only Operations

The following command prefixes are considered read-only and execute without approval:

- Basic operations: `describe`, `list`, `get`, `show`, `view`, `ls`, `head`
- Service-specific: `ec2 describe`, `s3 ls`, `iam list`, `rds describe`, etc.
- Full list available in the source code

## Configuration

The server automatically reads your AWS configuration from:
- `~/.aws/config` - For profiles and default settings
- `~/.aws/credentials` - For access keys (handled by AWS CLI)

## Integration with MCP Clients

### Claude Desktop

1. Open Claude Desktop settings
2. Navigate to Developer > Edit Config
3. Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aws-mcp-server": {
      "command": "python",
      "args": ["/path/to/aws-mcp-server/aws_mcp_server.py"],
      "env": {}
    }
  }
}
```

4. Restart Claude Desktop
5. The AWS tools will appear in Claude's tool menu

**Permission Control:**

Claude Desktop will automatically prompt for approval before each write command due to the tool naming. This is enforced by the MCP server design and cannot be disabled.

### VS Code Copilot

VS Code Copilot can use either the stdio or HTTP MCP server:

#### Option 1: HTTP MCP Server (Recommended)
```bash
python aws_mcp_http_server.py --port 8000
```

Configure VS Code Copilot to connect to:
- **Direct MCP**: `POST http://localhost:8000/` (supports direct JSON-RPC)

#### Option 2: stdio MCP Server
```json
{
  "github.copilot.chat.localmcpServers": [
    {
      "name": "aws-mcp-server",
      "command": "python",
      "args": ["/path/to/aws-mcp-server/aws_mcp_server.py"],
      "env": {}
    }
  ]
}
```

**Permission Control:**

Both servers enforce the same permission model using separate tools for read vs write operations.

### OpenAI Codex / Custom Integrations

For custom integrations, you'll need to:

1. Create an MCP client that connects to the server via stdio
2. Example client code:

```python
import subprocess
import json

# Start the MCP server
process = subprocess.Popen(
    ['python', 'aws_mcp_server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send MCP protocol messages
request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "execute_aws_command",
        "arguments": {"command": "s3 ls"}
    },
    "id": 1
}

process.stdin.write(json.dumps(request) + '\n')
process.stdin.flush()

# Read response
response = process.stdout.readline()
print(json.loads(response))
```

3. Implement the full MCP protocol for robust communication

## Development

To extend the read-only command list, modify the `_get_read_only_prefixes()` method in `aws_mcp_server.py`.

## License

MIT