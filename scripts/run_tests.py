#!/usr/bin/env python3
"""
Test runner script for AgentHub Registry.
Provides different test execution modes for development and CI/CD.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description="Running command"):
    """Run a shell command and handle errors."""
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"Command: {' '.join(cmd)}")
    print('=' * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return e.returncode


def run_unit_tests(coverage=False, verbose=False):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "-m", "unit"]
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running unit tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running integration tests")


def run_api_tests(verbose=False):
    """Run API tests."""
    cmd = ["python", "-m", "pytest", "-m", "api"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running API tests")


def run_service_tests(verbose=False):
    """Run service layer tests."""
    cmd = ["python", "-m", "pytest", "-m", "services"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running service tests")


def run_model_tests(verbose=False):
    """Run model tests."""
    cmd = ["python", "-m", "pytest", "-m", "models"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running model tests")


def run_all_tests(coverage=False, verbose=False, fail_fast=False):
    """Run all tests."""
    cmd = ["python", "-m", "pytest"]
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    if verbose:
        cmd.append("-v")
    
    if fail_fast:
        cmd.append("-x")
    
    return run_command(cmd, "Running all tests")


def run_fast_tests():
    """Run fast tests only (excluding slow marked tests)."""
    cmd = ["python", "-m", "pytest", "-m", "not slow"]
    
    return run_command(cmd, "Running fast tests")


def run_slow_tests():
    """Run slow tests only."""
    cmd = ["python", "-m", "pytest", "-m", "slow"]
    
    return run_command(cmd, "Running slow tests")


def run_linting():
    """Run code linting."""
    commands = [
        (["python", "-m", "black", "--check", "app", "tests"], "Checking code formatting with Black"),
        (["python", "-m", "isort", "--check-only", "app", "tests"], "Checking import sorting with isort"),
        (["python", "-m", "flake8", "app", "tests"], "Running flake8 linting"),
        (["python", "-m", "mypy", "app"], "Running type checking with mypy"),
    ]
    
    failed = False
    for cmd, description in commands:
        if run_command(cmd, description) != 0:
            failed = True
    
    return 1 if failed else 0


def run_security_checks():
    """Run security checks."""
    # Check if bandit is installed
    try:
        subprocess.run(["python", "-m", "bandit", "--version"], 
                      check=True, capture_output=True)
        return run_command(
            ["python", "-m", "bandit", "-r", "app", "-f", "json"],
            "Running security checks with bandit"
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Bandit not installed, skipping security checks")
        print("   Install with: pip install bandit")
        return 0


def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/15",
        "SECRET_KEY": "test-secret-key",
        "GITHUB_CLIENT_ID": "test-client-id",
        "GITHUB_CLIENT_SECRET": "test-client-secret",
        "GITHUB_OAUTH_REDIRECT_URI": "http://localhost:8000/api/v1/auth/github/callback",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "S3_BUCKET_NAME": "test-bucket",
        "PYTHONPATH": str(Path.cwd()),
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("✅ Test environment configured")


def check_dependencies():
    """Check if all required test dependencies are installed."""
    required_packages = [
        "pytest",
        "pytest-asyncio", 
        "pytest-cov",
        "httpx",
        "factory-boy",
    ]
    
    missing = []
    for package in required_packages:
        try:
            subprocess.run([sys.executable, "-c", f"import {package.replace('-', '_')}"], 
                          check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required test dependencies are installed")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for AgentHub Registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py --all --coverage          # Run all tests with coverage
  python scripts/run_tests.py --unit --verbose          # Run unit tests with verbose output
  python scripts/run_tests.py --fast                    # Run fast tests only
  python scripts/run_tests.py --lint                    # Run linting checks
  python scripts/run_tests.py --ci                      # Run CI pipeline (all checks)
        """
    )
    
    # Test type options
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--api", action="store_true", help="Run API tests")
    parser.add_argument("--services", action="store_true", help="Run service tests")
    parser.add_argument("--models", action="store_true", help="Run model tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--slow", action="store_true", help="Run slow tests only")
    
    # Code quality options
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--security", action="store_true", help="Run security checks")
    
    # Test options
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")
    
    # CI/CD options
    parser.add_argument("--ci", action="store_true", help="Run full CI pipeline")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    
    args = parser.parse_args()
    
    # If no specific tests selected, default to all
    if not any([args.all, args.unit, args.integration, args.api, args.services, 
                args.models, args.fast, args.slow, args.lint, args.security, 
                args.ci, args.check_deps]):
        args.all = True
    
    print("🧪 AgentHub Registry Test Runner")
    print("=" * 60)
    
    # Set up test environment
    setup_test_environment()
    
    # Check dependencies
    if args.check_deps:
        return 0 if check_dependencies() else 1
    
    if not check_dependencies():
        return 1
    
    exit_code = 0
    
    # Run CI pipeline
    if args.ci:
        print("\n🚀 Running full CI pipeline...")
        steps = [
            (lambda: run_linting(), "Linting"),
            (lambda: run_security_checks(), "Security checks"),
            (lambda: run_unit_tests(coverage=True), "Unit tests"),
            (lambda: run_integration_tests(), "Integration tests"),
            (lambda: run_api_tests(), "API tests"),
        ]
        
        for step_func, step_name in steps:
            print(f"\n📋 CI Step: {step_name}")
            if step_func() != 0:
                print(f"❌ CI pipeline failed at: {step_name}")
                return 1
        
        print("\n✅ CI pipeline completed successfully!")
        return 0
    
    # Run specific test types
    if args.lint:
        exit_code = max(exit_code, run_linting())
    
    if args.security:
        exit_code = max(exit_code, run_security_checks())
    
    if args.unit:
        exit_code = max(exit_code, run_unit_tests(args.coverage, args.verbose))
    
    if args.integration:
        exit_code = max(exit_code, run_integration_tests(args.verbose))
    
    if args.api:
        exit_code = max(exit_code, run_api_tests(args.verbose))
    
    if args.services:
        exit_code = max(exit_code, run_service_tests(args.verbose))
    
    if args.models:
        exit_code = max(exit_code, run_model_tests(args.verbose))
    
    if args.fast:
        exit_code = max(exit_code, run_fast_tests())
    
    if args.slow:
        exit_code = max(exit_code, run_slow_tests())
    
    if args.all:
        exit_code = max(exit_code, run_all_tests(args.coverage, args.verbose, args.fail_fast))
    
    # Print summary
    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ All tests passed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 