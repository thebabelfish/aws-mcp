# Security Configuration Guide

This AWS MCP server implements a **dual-layer security model** for maximum protection:

## Layer 1: LLM Client Permissions (Recommended)
The AI client (Claude, VS Code Copilot) asks for permission before executing ANY tool.

## Layer 2: MCP Server Permissions (Fallback)
The MCP server requires terminal approval for write operations.

## Configuration Options

### Option 1: LLM-Only Permissions (Default & Recommended)

This approach uses only the LLM client for permissions, with no server-side prompts.

#### Claude Desktop Configuration:
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

#### VS Code Copilot Configuration:
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

### Option 2: Dual-Layer Security (Maximum Protection)

Keep both layers active - LLM prompts AND server-side approval for writes.

#### Claude Desktop Configuration:
```json
{
  "mcpServers": {
    "aws-mcp-server": {
      "command": "python",
      "args": ["/path/to/aws-mcp-server/aws_mcp_server.py", "--require-approval"],
      "env": {}
    }
  }
}
```

#### VS Code Copilot Configuration:
```json
{
  "github.copilot.chat.localmcpServers": [
    {
      "name": "aws-mcp-server",
      "command": "python",
      "args": ["/path/to/aws-mcp-server/aws_mcp_server.py", "--require-approval"],
      "env": {}
    }
  ]
}
```

### Option 3: Server-Only Permissions (Terminal-Based)

For clients that don't support permission prompts, disable LLM permissions and use terminal approval:

#### Claude Desktop:
```json
{
  "mcpServers": {
    "aws-mcp-server": {
      "command": "python",
      "args": ["/path/to/aws-mcp-server/aws_mcp_server.py", "--require-approval", "--dangerously-skip-permissions"],
      "env": {}
    }
  }
}
```

## Permission Granularity

### Read-Only Auto-Approval

To auto-approve only read operations in LLM clients:

#### Claude Desktop:
- Use "Allow always" only for read commands
- Manually approve write operations each time

#### VS Code Copilot:
- Use session auto-approval (click "Continue")
- Avoid global `chat.tools.autoApprove: true`

### Command-Specific Permissions

You can modify the server's read-only command list by editing `_get_read_only_prefixes()` in `aws_mcp_server.py`.

## Security Best Practices

1. **Start Conservative**: Begin with dual-layer security
2. **Test Thoroughly**: Verify permission prompts work as expected
3. **Monitor Usage**: Keep logs of executed commands
4. **Regular Audits**: Review and update read-only command lists
5. **Environment Separation**: Use different profiles for different environments

## Implementation Notes

- **Default behavior**: Server-side approval is disabled, LLM handles all permissions
- **Enhanced security**: Use `--require-approval` for dual-layer protection
- **User experience**: LLM permissions are more user-friendly than terminal prompts
- **Compatibility**: Some clients may not support fine-grained permission control
- **Testing**: Always test configuration changes in a safe environment first