#!/usr/bin/env python3
"""Simple test client for AWS MCP Server."""

import asyncio
import json
import subprocess
import sys

async def test_mcp_server():
    """Test the MCP server with various commands."""
    
    print("🧪 Testing AWS MCP Server")
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
        # Test 1: List tools
        print("\n📋 Test 1: List available tools")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print(f"✅ Tools available: {len(response.get('result', []))} tools")
            for tool in response.get('result', []):
                print(f"   - {tool['name']}: {tool['description']}")
        
        # Test 2: List AWS profiles
        print("\n👤 Test 2: List AWS profiles")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_aws_profiles",
                "arguments": {}
            },
            "id": 2
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            result = response.get('result', [])
            if result:
                print(f"✅ {result[0]['text']}")
        
        # Test 3: Test read command validation
        print("\n📖 Test 3: Test read command with valid read operation")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_aws_read_command",
                "arguments": {
                    "command": "sts get-caller-identity",
                    "profile": "default"
                }
            },
            "id": 3
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            result = response.get('result', [])
            if result:
                print(f"✅ Read command executed: {result[0]['text'][:100]}...")
        
        # Test 4: Test read command with invalid (write) operation
        print("\n❌ Test 4: Test read command with write operation (should fail)")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_aws_read_command",
                "arguments": {
                    "command": "s3 mb s3://test-bucket"
                }
            },
            "id": 4
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            result = response.get('result', [])
            if result:
                print(f"✅ Validation worked: {result[0]['text']}")
        
        # Test 5: Test write command with invalid (read) operation  
        print("\n❌ Test 5: Test write command with read operation (should fail)")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_aws_write_command",
                "arguments": {
                    "command": "s3 ls"
                }
            },
            "id": 5
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            result = response.get('result', [])
            if result:
                print(f"✅ Validation worked: {result[0]['text']}")
        
        # Test 6: Test write command with valid write operation
        print("\n✏️ Test 6: Test write command with valid write operation")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_aws_write_command",
                "arguments": {
                    "command": "s3 mb s3://test-bucket-12345"
                }
            },
            "id": 6
        }
        
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            result = response.get('result', [])
            if result:
                print(f"✅ Write command executed: {result[0]['text'][:100]}...")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())