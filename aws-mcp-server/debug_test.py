#!/usr/bin/env python3
"""Debug test for AWS MCP Server."""

import asyncio
import json
import subprocess
import sys

async def debug_mcp_server():
    """Debug the MCP server."""
    
    print("🐛 Debugging AWS MCP Server")
    print("=" * 50)
    
    # Start the MCP server
    process = subprocess.Popen(
        ['python', 'aws_mcp_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send a simple initialize request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        print("📤 Sending initialize request")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()
        
        # Read initialize response
        response_line = process.stdout.readline()
        print(f"📥 Initialize response: {response_line.strip()}")
        
        if response_line:
            try:
                response = json.loads(response_line.strip())
                print(f"✅ Initialize successful: {response.get('result', {}).get('capabilities', 'No capabilities')}")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse initialize response: {e}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        print("📤 Sending initialized notification")
        process.stdin.write(json.dumps(initialized_notification) + '\n')
        process.stdin.flush()
        
        # Now try to list tools
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        print("📤 Sending tools/list request")
        process.stdin.write(json.dumps(tools_request) + '\n')
        process.stdin.flush()
        
        # Read tools response
        response_line = process.stdout.readline()
        print(f"📥 Tools response: {response_line.strip()}")
        
        if response_line:
            try:
                response = json.loads(response_line.strip())
                tools = response.get('result', {}).get('tools', [])
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description']}")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse tools response: {e}")
        
        # Check stderr for any errors
        stderr_output = process.stderr.read()
        if stderr_output:
            print(f"⚠️ Stderr output: {stderr_output}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(debug_mcp_server())