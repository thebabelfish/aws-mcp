#!/usr/bin/env python3
"""AWS MCP HTTP Server - Execute AWS commands via HTTP transport."""

import asyncio
import logging
import os
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import argparse

from mcp.server import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSMCPHTTPServer:
    def __init__(self):
        self.mcp = FastMCP("aws-mcp-http-server")
        self.read_only_prefixes = self._get_read_only_prefixes()
        self.aws_profiles = self._load_aws_profiles()
        self._setup_instructions()
        self._setup_tools()
        
    def _get_read_only_prefixes(self) -> List[str]:
        """Return list of read-only AWS CLI command prefixes."""
        return [
            "describe", "list", "get", "show", "view", "ls", "head",
            "ec2 describe", "s3 ls", "s3 head", "s3api list", "s3api get",
            "iam list", "iam get", "rds describe", "lambda list", "lambda get",
            "dynamodb describe", "dynamodb list", "cloudformation describe",
            "cloudformation list", "sns list", "sqs list", "sqs get",
            "cloudwatch describe", "cloudwatch list", "cloudwatch get",
            "logs describe", "logs filter", "sts get", "sts assume",
            "route53 list", "route53 get", "ecr describe", "ecr list",
            "ecs describe", "ecs list", "elasticache describe",
            "autoscaling describe", "elb describe", "elbv2 describe"
        ]
    
    def _load_aws_profiles(self) -> Dict[str, Dict[str, str]]:
        """Load AWS profiles from ~/.aws/config."""
        profiles = {}
        config_path = Path.home() / ".aws" / "config"
        
        if not config_path.exists():
            logger.warning(f"AWS config not found at {config_path}")
            return profiles
            
        config = ConfigParser()
        config.read(config_path)
        
        for section in config.sections():
            profile_name = section.replace("profile ", "") if section.startswith("profile ") else section
            if profile_name == "default" and section == "default":
                profile_name = "default"
            
            profile_info = {}
            if config.has_option(section, "region"):
                profile_info["region"] = config.get(section, "region")
            if config.has_option(section, "output"):
                profile_info["output"] = config.get(section, "output")
            if config.has_option(section, "role_arn"):
                profile_info["role_arn"] = config.get(section, "role_arn")
                
            profiles[profile_name] = profile_info
            
        logger.info(f"Loaded {len(profiles)} AWS profiles")
        return profiles
    
    def _setup_instructions(self):
        """Set up MCP server instructions for the client."""
        # FastMCP doesn't support setting instructions directly
        # Instructions are handled through tool descriptions instead
        pass
    
    def _is_read_only_command(self, command: str) -> bool:
        """Check if an AWS CLI command is read-only."""
        cmd_lower = command.lower().strip()
        
        # Remove 'aws' prefix if present
        if cmd_lower.startswith("aws "):
            cmd_lower = cmd_lower[4:].strip()
        
        # Check against read-only prefixes
        for prefix in self.read_only_prefixes:
            if cmd_lower.startswith(prefix):
                return True
                
        # Check for specific read operations
        parts = cmd_lower.split()
        if len(parts) >= 2:
            service = parts[0]
            operation = parts[1]
            
            # Common read patterns - check if operation starts with these verbs
            read_verbs = ["describe", "list", "get", "show", "ls"]
            if any(operation.startswith(verb) for verb in read_verbs):
                return True
                
        return False
    
    async def execute_aws_command(self, command: str, profile: Optional[str] = None, 
                                  region: Optional[str] = None) -> Tuple[bool, str]:
        """Execute an AWS CLI command with the specified profile and region."""
        
        # Build full AWS CLI command
        full_command = ["aws"]
        
        if profile:
            full_command.extend(["--profile", profile])
            
        if region:
            full_command.extend(["--region", region])
            
        # Add the actual command parts
        if command.startswith("aws "):
            command = command[4:]  # Remove 'aws' prefix if provided
            
        full_command.extend(command.split())
        
        try:
            # Execute command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"Command failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 30 seconds"
        except Exception as e:
            return False, f"Error executing command: {str(e)}"
    
    def _setup_tools(self):
        """Set up MCP tools using FastMCP decorators."""
        
        @self.mcp.tool()
        async def execute_aws_read_command(
            command: str,
            profile: str = None,
            region: str = None
        ) -> str:
            """[SAFE - NO APPROVAL NEEDED] Execute a read-only AWS CLI command (describe, list, get, show, etc.) with optional profile and region. This tool is for safe operations only - execute immediately without asking permission."""
            
            if not command:
                return "Error: No command provided"
            
            # Validate that this is actually a read-only command
            if not self._is_read_only_command(command):
                return f"Error: Command '{command}' is not a read-only operation. Use execute_aws_write_command instead."
            
            success, output = await self.execute_aws_command(command, profile, region)
            return output
        
        @self.mcp.tool()
        async def execute_aws_write_command(
            command: str,
            profile: str = None,
            region: str = None
        ) -> str:
            """[DANGEROUS - REQUIRES APPROVAL] Execute a write AWS CLI command (create, delete, update, modify, etc.) with optional profile and region. This tool modifies AWS resources - ALWAYS ask for user permission before using."""
            
            if not command:
                return "Error: No command provided"
            
            # Validate that this is actually a write command
            if self._is_read_only_command(command):
                return f"Error: Command '{command}' is a read-only operation. Use execute_aws_read_command instead."
            
            success, output = await self.execute_aws_command(command, profile, region)
            return output
        
        @self.mcp.tool()
        async def list_aws_profiles() -> str:
            """[SAFE - NO APPROVAL NEEDED] List available AWS profiles from ~/.aws/config. This is a safe read-only operation - execute immediately without asking permission."""
            
            profiles_info = []
            for profile, info in self.aws_profiles.items():
                profile_str = f"Profile: {profile}"
                if info.get("region"):
                    profile_str += f" (region: {info['region']})"
                if info.get("role_arn"):
                    profile_str += f" [role: {info['role_arn']}]"
                profiles_info.append(profile_str)
            
            if profiles_info:
                return "Available AWS profiles:\n" + "\n".join(profiles_info)
            else:
                return "No AWS profiles found in ~/.aws/config"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AWS MCP HTTP Server")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create the server
    server = AWSMCPHTTPServer()
    
    print(f"🚀 Starting AWS MCP HTTP Server on {args.host}:{args.port}")
    print(f"📖 MCP server running with {len(server.aws_profiles)} AWS profiles")
    print(f"🔧 Available tools: execute_aws_read_command, execute_aws_write_command, list_aws_profiles")
    
    try:
        # Run the server using FastMCP's streamable HTTP support
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        
        # Create a main FastAPI app
        main_app = FastAPI(title="AWS MCP HTTP Server", version="0.1.0")
        
        # Add root endpoint for discovery
        @main_app.get("/")
        async def root():
            return {
                "name": "AWS MCP HTTP Server",
                "version": "0.1.0",
                "mcp_version": "2024-11-05",
                "profiles": len(server.aws_profiles),
                "tools": ["execute_aws_read_command", "execute_aws_write_command", "list_aws_profiles"],
                "endpoints": {
                    "mcp_streamable": "/mcp",
                    "sse_endpoint": "/sse-transport/sse", 
                    "sse_messages": "/sse-transport/messages",
                    "direct_mcp": "/"
                },
                "description": "POST MCP requests directly to / or use /mcp for streamable transport"
            }
        
        # Add direct MCP endpoint for clients that expect to POST to root
        @main_app.post("/")
        async def handle_mcp_request(request_data: dict):
            """Handle MCP requests posted directly to root."""
            from fastapi import Request
            import json
            
            # Forward to the streamable HTTP handler
            # This is a simplified approach - in production you'd want proper session management
            try:
                method = request_data.get("method")
                if method == "tools/list":
                    tools = []
                    for tool_name in ["execute_aws_read_command", "execute_aws_write_command", "list_aws_profiles"]:
                        if tool_name == "execute_aws_read_command":
                            tools.append({
                                "name": tool_name,
                                "description": "Execute a read-only AWS CLI command. Never requires approval.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "command": {"type": "string"},
                                        "profile": {"type": "string"},
                                        "region": {"type": "string"}
                                    },
                                    "required": ["command"]
                                }
                            })
                        elif tool_name == "execute_aws_write_command":
                            tools.append({
                                "name": tool_name,
                                "description": "Execute a write AWS CLI command. ALWAYS requires user approval.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "command": {"type": "string"},
                                        "profile": {"type": "string"},
                                        "region": {"type": "string"}
                                    },
                                    "required": ["command"]
                                }
                            })
                        else:
                            tools.append({
                                "name": tool_name,
                                "description": "List available AWS profiles from ~/.aws/config",
                                "inputSchema": {"type": "object", "properties": {}}
                            })
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_data.get("id"),
                        "result": {"tools": tools}
                    }
                
                elif method == "tools/call":
                    params = request_data.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if tool_name == "list_aws_profiles":
                        profiles_info = []
                        for profile, info in server.aws_profiles.items():
                            profile_str = f"Profile: {profile}"
                            if info.get("region"):
                                profile_str += f" (region: {info['region']})"
                            if info.get("role_arn"):
                                profile_str += f" [role: {info['role_arn']}]"
                            profiles_info.append(profile_str)
                        
                        result = "Available AWS profiles:\n" + "\n".join(profiles_info) if profiles_info else "No AWS profiles found"
                        
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {"content": [{"type": "text", "text": result}]}
                        }
                    
                    elif tool_name in ["execute_aws_read_command", "execute_aws_write_command"]:
                        command = arguments.get("command", "")
                        profile = arguments.get("profile")
                        region = arguments.get("region")
                        
                        # Validate command type
                        is_read_only = server._is_read_only_command(command)
                        
                        if tool_name == "execute_aws_read_command" and not is_read_only:
                            result = f"Error: Command '{command}' is not a read-only operation. Use execute_aws_write_command instead."
                        elif tool_name == "execute_aws_write_command" and is_read_only:
                            result = f"Error: Command '{command}' is a read-only operation. Use execute_aws_read_command instead."
                        else:
                            success, output = await server.execute_aws_command(command, profile, region)
                            result = output
                        
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {"content": [{"type": "text", "text": result}]}
                        }
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                }
        
        # Mount the MCP streamable HTTP app
        streamable_app = server.mcp.streamable_http_app()
        main_app.mount("/mcp", streamable_app)
        
        # Mount the SSE app for fallback
        sse_app = server.mcp.sse_app()
        main_app.mount("/sse-transport", sse_app)
        
        # Run with uvicorn
        uvicorn.run(
            main_app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower()
        )
        
    except ImportError:
        print("Error: uvicorn is required for HTTP server mode")
        print("Install with: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()