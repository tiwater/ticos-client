#!/usr/bin/env python3
"""
Check the environment and dependencies for TicosClient.

This script verifies that all required dependencies are installed and
that the environment is properly set up for running TicosClient.
"""
import importlib.metadata
import platform
import sys
from typing import Dict, List, Tuple

# Required packages and their minimum versions
REQUIRED_PACKAGES = {
    "fastapi": "0.68.0",
    "uvicorn": "0.15.0",
    "pydantic": "1.8.0",
    "websockets": "10.0",
    "httpx": "0.23.0",
    "sqlalchemy": "1.4.0",
    "python-dotenv": "0.19.0",
    "python-jose": "3.3.0",
    "passlib": "1.7.4",
    "alembic": "1.7.0",
    "python-dateutil": "2.8.2",
}

# Optional packages (for development and testing)
OPTIONAL_PACKAGES = {
    "pytest": "6.2.5",
    "pytest-cov": "2.12.1",
    "pytest-asyncio": "0.15.1",
    "black": "21.7b0",
    "isort": "5.9.0",
    "flake8": "3.9.2",
    "mypy": "0.910",
    "sphinx": "4.0.2",
    "sphinx-rtd-theme": "0.5.2",
    "sphinx-autodoc-typehints": "1.12.0",
}


def get_package_version(package_name: str) -> Tuple[bool, str]:
    """Get the installed version of a package."""
    try:
        version = importlib.metadata.version(package_name)
        return True, version
    except importlib.metadata.PackageNotFoundError:
        return False, "Not installed"


def check_python_version() -> Tuple[bool, str]:
    """Check if the Python version meets the requirements."""
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) < (3, 7):
        return False, f"Python {major}.{minor} (requires 3.7+)"
    return True, f"Python {major}.{minor}"


def check_os() -> Tuple[bool, str]:
    """Check the operating system."""
    system = platform.system()
    release = platform.release()
    return True, f"{system} {release}"


def check_packages(required: bool = True) -> Tuple[bool, Dict[str, Tuple[bool, str, str]]]:
    """Check if required packages are installed and meet version requirements."""
    packages = REQUIRED_PACKAGES if required else OPTIONAL_PACKAGES
    all_ok = True
    results = {}
    
    for package, min_version in packages.items():
        installed, version = get_package_version(package)
        if not installed:
            status = "❌ Not installed"
            all_ok = False
        else:
            # Simple version comparison
            installed_parts = list(map(int, version.split('.')[:3]))
            min_parts = list(map(int, min_version.split('.')[:3]))
            
            if installed_parts < min_parts:
                status = f"⚠️  Installed: {version} (requires {min_version}+)"
                all_ok = False
            else:
                status = f"✅ {version}"
        
        results[package] = (installed, min_version, status)
    
    return all_ok, results


def print_results(
    title: str, 
    results: Dict[str, Tuple[bool, str, str]],
    verbose: bool = False
) -> None:
    """Print the results of environment checks."""
    print(f"\n{title}:")
    print("=" * (len(title) + 1))
    
    max_pkg_len = max(len(pkg) for pkg in results.keys()) + 2
    max_ver_len = max(len(ver) for _, ver, _ in results.values()) + 2
    
    for package, (_, min_version, status) in results.items():
        if verbose or "❌" in status or "⚠️" in status:
            print(f"{package:<{max_pkg_len}} {min_version:<{max_ver_len}} {status}")
    
    if not verbose:
        print("(Use --verbose to see all packages)")


def main():
    """Main function to check the environment."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check TicosClient environment")
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Show all packages, not just problems"
    )
    args = parser.parse_args()
    
    print("\nTicosClient Environment Check")
    print("=" * 30)
    
    # Check Python version
    py_ok, py_version = check_python_version()
    print(f"\nPython: {py_version} {"✅" if py_ok else "❌"}")
    
    # Check OS
    os_ok, os_info = check_os()
    print(f"OS: {os_info} {"✅" if os_ok else "❌"}")
    
    # Check required packages
    req_ok, req_results = check_packages(required=True)
    print_results("Required Packages", req_results, args.verbose)
    
    # Check optional packages
    opt_ok, opt_results = check_packages(required=False)
    print_results("Optional Packages", opt_results, args.verbose)
    
    # Print summary
    print("\nSummary:")
    print("=" * 7)
    print(f"Python Version: {"✅" if py_ok else "❌"}")
    print(f"Required Packages: {"✅" if req_ok else "❌"}")
    print(f"Optional Packages: {"✅" if opt_ok else "⚠️ "}")
    
    if not (py_ok and req_ok):
        print("\n❌ Some requirements are not met. Please install missing packages.")
        sys.exit(1)
    else:
        print("\n✅ Environment is properly configured!")
        sys.exit(0)


if __name__ == "__main__":
    main()
