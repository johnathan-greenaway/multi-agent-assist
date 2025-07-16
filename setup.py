from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="multi-agent-mcp",
    version="0.1.0",
    author="Multi-Agent MCP Team",
    description="Multi-agent collaboration system for Claude Code and Gemini Code Assist",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/multi-agent-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiofiles>=23.0.0",
        "asyncio>=3.4.3",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "watchdog>=3.0.0",
        "filelock>=3.12.0",
        "jsonschema>=4.0.0",
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "multi-agent-mcp=multi_agent_mcp.cli:main",
            "mcp-monitor=multi_agent_mcp.monitor:main",
        ],
    },
)