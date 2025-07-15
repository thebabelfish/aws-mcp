from setuptools import setup, find_packages

setup(
    name="aws-mcp-server",
    version="0.1.0",
    description="AWS MCP Server - Execute AWS commands via Model Context Protocol",
    author="Your Name",
    py_modules=["aws_mcp_server"],
    install_requires=[
        "mcp",
        "boto3",
        "click",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "aws-mcp-server=aws_mcp_server:main",
        ],
    },
    python_requires=">=3.8",
)