"""Setup configuration for HelixOps."""

from setuptools import setup, find_packages

setup(
    name="helixops",
    version="1.0.0",
    description="Distributed workflow orchestration engine",
    author="HelixOps Contributors",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "typer>=0.9.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "helixops=helixops.cli.app:app",
        ],
    },
)
