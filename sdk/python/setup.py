from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ticos-client",
    version="0.5.8",  # Major version bump due to significant changes
    author="Ticos Team",
    author_email="admin@tiwater.com",
    description="A client SDK for the Ticos Agent system with HTTP and WebSocket support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tiwater/ticos-client",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "ticos_client": ["py.typed"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0,<1.0.0",
        "uvicorn>=0.15.0,<1.0.0",
        "pydantic>=1.8.0,<2.0.0",
        "python-multipart>=0.0.5,<1.0.0",
        "python-jose[cryptography]>=3.3.0,<4.0.0",
        "passlib[bcrypt]>=1.7.4,<2.0.0",
        "python-dotenv>=0.19.0,<1.0.0",
        "SQLAlchemy>=1.4.0,<2.0.0",
        "alembic>=1.7.0,<2.0.0",
        "python-dateutil>=2.8.2,<3.0.0",
        "toml>=0.10.0,<1.0.0",
        "uvicorn[standard]>=0.15.0,<1.0.0",
        "requests>=2.26.0,<3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "mypy>=0.910",
            "black>=21.7b0",
            "isort>=5.9.0",
            "flake8>=3.9.0",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/tiwater/ticos-client/issues",
        "Source": "https://github.com/tiwater/ticos-client",
    },
)
