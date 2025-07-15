# Test Commands for AWS MCP Server

## Quick Test Script

```bash
# 1. First, activate the virtual environment
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python aws_mcp_server.py
```

## Test Commands to Try

### Read-Only Commands (No Approval Needed)

```bash
# List S3 buckets
{"tool": "execute_aws_read_command", "arguments": {"command": "s3 ls"}}

# Describe EC2 instances
{"tool": "execute_aws_read_command", "arguments": {"command": "ec2 describe-instances"}}

# List IAM users
{"tool": "execute_aws_read_command", "arguments": {"command": "iam list-users"}}

# Get caller identity
{"tool": "execute_aws_read_command", "arguments": {"command": "sts get-caller-identity"}}

# List available profiles
{"tool": "list_aws_profiles", "arguments": {}}
```

### Write Commands (Always Requires Approval)

```bash
# Create S3 bucket (will prompt for approval)
{"tool": "execute_aws_write_command", "arguments": {"command": "s3 mb s3://test-bucket-12345", "profile": "dev"}}

# Create EC2 tag (will prompt for approval)
{"tool": "execute_aws_write_command", "arguments": {"command": "ec2 create-tags --resources i-1234567890abcdef0 --tags Key=Name,Value=MyInstance"}}
```

## Integration with MCP Clients

### Claude Desktop Setup

1. Find your Claude Desktop config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add this configuration:
```json
{
  "mcpServers": {
    "aws-mcp-server": {
      "command": "python",
      "args": ["/absolute/path/to/aws-mcp-server/aws_mcp_server.py"],
      "env": {}
    }
  }
}
```

3. Restart Claude Desktop

4. Test by asking Claude: "Can you list my AWS profiles?" or "Show me my S3 buckets"

### VS Code Copilot Setup

1. Open VS Code settings.json:
   - Cmd+Shift+P → "Preferences: Open Settings (JSON)"

2. Add this configuration:
```json
{
  "github.copilot.chat.localmcpServers": [
    {
      "name": "aws-mcp-server",
      "command": "python",
      "args": ["/absolute/path/to/aws-mcp-server/aws_mcp_server.py"],
      "env": {}
    }
  ]
}
```

3. Reload VS Code window (Cmd+Shift+P → "Developer: Reload Window")

4. In Copilot Chat, use @aws-mcp-server to invoke AWS commands:
   - "@aws-mcp-server list my S3 buckets"
   - "@aws-mcp-server show me EC2 instances in us-east-1"

### Debugging Tips

- Check VS Code Output panel → "GitHub Copilot Chat" for errors
- Ensure Python is in your system PATH
- Use absolute paths in the configuration
- For virtual environment, you might need:
  ```json
  {
    "command": "/path/to/venv/bin/python",
    "args": ["/path/to/aws-mcp-server/aws_mcp_server.py"]
  }
  ```