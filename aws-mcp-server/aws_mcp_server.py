#!/usr/bin/env python3
"""AWS MCP Server - Execute AWS commands with profile and region awareness."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import argparse

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSMCPServer:
    def __init__(self):
        self.server = Server("aws-mcp-server")
        self.read_only_prefixes = self._get_read_only_prefixes()
        self.aws_profiles = self._load_aws_profiles()
        self._setup_instructions()
        
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
        self.server.instructions = """
You are connected to an AWS MCP server with an ENFORCED permission model. Follow these rules exactly:

🔥 CRITICAL PERMISSION RULES 🔥
1. execute_aws_read_command: NEVER ask for permission. These are safe read-only operations (list, describe, get, show, ls, head). Execute immediately without any confirmation.

2. execute_aws_write_command: ALWAYS ask for permission. These modify AWS resources (create, delete, update, modify, put, mb, cp, sync, rm).

3. list_aws_profiles: NEVER ask for permission. This just lists available AWS profiles from ~/.aws/config.

The server validates commands - you cannot use the wrong tool for the wrong operation type. The tool separation exists specifically so you can execute read operations without asking and always ask for write operations.

IMPORTANT: Do not ask "Are you sure you want to..." for read-only commands. Just execute them immediately.
"""
    
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
            
            # Common read patterns
            if operation in ["describe", "list", "get", "show", "ls"]:
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
    
    def setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return available tools."""
            return [
                types.Tool(
                    name="execute_aws_read_command",
                    description="[SAFE - NO APPROVAL NEEDED] Execute a read-only AWS CLI command (describe, list, get, show, etc.) with optional profile and region. This tool is for safe operations only - execute immediately without asking permission.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "AWS CLI command to execute (without 'aws' prefix). Must be read-only."
                            },
                            "profile": {
                                "type": "string",
                                "description": "AWS profile to use (optional)"
                            },
                            "region": {
                                "type": "string",
                                "description": "AWS region to use (optional)"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                types.Tool(
                    name="execute_aws_write_command",
                    description="Execute a write AWS CLI command (create, delete, update, modify, etc.) with optional profile and region. ALWAYS requires user approval.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "AWS CLI command to execute (without 'aws' prefix). Must be a write operation."
                            },
                            "profile": {
                                "type": "string",
                                "description": "AWS profile to use (optional)"
                            },
                            "region": {
                                "type": "string",
                                "description": "AWS region to use (optional)"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                types.Tool(
                    name="list_aws_profiles",
                    description="List available AWS profiles from ~/.aws/config",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent]:
            """Handle tool execution requests."""
            
            if name == "execute_aws_read_command":
                command = arguments.get("command", "")
                profile = arguments.get("profile")
                region = arguments.get("region")
                
                if not command:
                    return [types.TextContent(
                        type="text",
                        text="Error: No command provided"
                    )]
                
                # Validate that this is actually a read-only command
                if not self._is_read_only_command(command):
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Command '{command}' is not a read-only operation. Use execute_aws_write_command instead."
                    )]
                
                success, output = await self.execute_aws_command(command, profile, region)
                
                return [types.TextContent(
                    type="text",
                    text=output
                )]
                
            elif name == "execute_aws_write_command":
                command = arguments.get("command", "")
                profile = arguments.get("profile")
                region = arguments.get("region")
                
                if not command:
                    return [types.TextContent(
                        type="text",
                        text="Error: No command provided"
                    )]
                
                # Validate that this is actually a write command
                if self._is_read_only_command(command):
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Command '{command}' is a read-only operation. Use execute_aws_read_command instead."
                    )]
                
                success, output = await self.execute_aws_command(command, profile, region)
                
                return [types.TextContent(
                    type="text",
                    text=output
                )]
                
            elif name == "list_aws_profiles":
                profiles_info = []
                for profile, info in self.aws_profiles.items():
                    profile_str = f"Profile: {profile}"
                    if info.get("region"):
                        profile_str += f" (region: {info['region']})"
                    if info.get("role_arn"):
                        profile_str += f" [role: {info['role_arn']}]"
                    profiles_info.append(profile_str)
                
                if profiles_info:
                    return [types.TextContent(
                        type="text",
                        text="Available AWS profiles:\n" + "\n".join(profiles_info)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="No AWS profiles found in ~/.aws/config"
                    )]
                    
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
    
    async def run(self):
        """Run the MCP server."""
        self.setup_handlers()
        
        # Use MCP's stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    """Main entry point."""
    server = AWSMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())