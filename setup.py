from setuptools import setup, find_packages

setup(
    name="boarding-mcp-server",
    version="0.1.0",
    description="MCP Server for Onboarding Management",
    author="Girish",
    author_email="girish12n@gmail.com",
    packages=find_packages(exclude=["tests*", "*.tests", "*.tests.*"]),
    python_requires=">=3.8",
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
        "sqlalchemy",
        "alembic",
        "psycopg2-binary",      # or asyncpg if using async
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        "httpx",
        "mcp",
        "google-generativeai",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
            "isort",
        ],
        "test": [
            "pytest",
            "pytest-asyncio",
            "httpx",
        ],
    },
    entry_points={
        "console_scripts": [
            "boarding-server=app.main:main",  # Adjust if you have a main function
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
