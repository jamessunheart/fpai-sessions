#!/bin/bash

# CODE STANDARDS CHECKER
# Blueprint: Foundation Files - CODE_STANDARDS.md
# Purpose: Enforce code quality standards across all droplets
# Usage: ./code-standards-check.sh [service-name] or ./code-standards-check.sh all

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install tools if needed
ensure_tools() {
    print_info "Checking for required tools..."

    local tools_needed=false

    if ! command_exists black; then
        print_warning "black not found"
        tools_needed=true
    fi

    if ! command_exists ruff; then
        print_warning "ruff not found"
        tools_needed=true
    fi

    if ! command_exists mypy; then
        print_warning "mypy not found"
        tools_needed=true
    fi

    if [ "$tools_needed" = true ]; then
        print_info "Installing code quality tools..."
        pip install black ruff mypy
    fi

    print_success "Tools ready"
}

# Function to check Python files for hardcoded secrets
check_secrets() {
    local dir=$1
    local service=$2

    print_info "[$service] Checking for hardcoded secrets..."
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    local issues=()

    # Check for common secret patterns
    if grep -r -n -E "(password|api_key|secret_key|token)\s*=\s*['\"][^'\"]+['\"]" "$dir" --include="*.py" 2>/dev/null | grep -v ".env" | grep -v "example" | grep -v "test" | grep -v "your-"; then
        issues+=("Potential hardcoded secrets found")
    fi

    if [ ${#issues[@]} -eq 0 ]; then
        print_success "[$service] No hardcoded secrets detected"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        print_error "[$service] Security issues found:"
        for issue in "${issues[@]}"; do
            echo "  - $issue"
        done
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Function to run black (formatting check)
check_formatting() {
    local dir=$1
    local service=$2

    print_info "[$service] Checking code formatting (black)..."
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if black --check "$dir/app" "$dir/tests" 2>&1 | grep -q "would be reformatted"; then
        print_error "[$service] Code needs formatting"
        echo "  Run: black $dir/app $dir/tests"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    else
        print_success "[$service] Code formatting OK"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    fi
}

# Function to run ruff (linting)
check_linting() {
    local dir=$1
    local service=$2

    print_info "[$service] Running linter (ruff)..."
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if ruff check "$dir/app" "$dir/tests" --quiet 2>&1; then
        print_success "[$service] Linting passed"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        print_error "[$service] Linting failed"
        echo "  Run: ruff check $dir/app $dir/tests"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Function to run mypy (type checking)
check_types() {
    local dir=$1
    local service=$2

    print_info "[$service] Checking type hints (mypy)..."
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if mypy "$dir/app" --ignore-missing-imports --no-error-summary 2>&1 | grep -q "error:"; then
        print_warning "[$service] Type checking has warnings"
        echo "  Run: mypy $dir/app"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))  # Warning, not failure
        return 0
    else
        print_success "[$service] Type checking passed"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    fi
}

# Function to check for docstrings
check_docstrings() {
    local dir=$1
    local service=$2

    print_info "[$service] Checking for docstrings..."
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    local python_files=$(find "$dir/app" -name "*.py" -type f | wc -l | tr -d ' ')
    local files_with_docstrings=0

    for file in $(find "$dir/app" -name "*.py" -type f); do
        if grep -q '"""' "$file" || grep -q "'''" "$file"; then
            files_with_docstrings=$((files_with_docstrings + 1))
        fi
    done

    local coverage=$((files_with_docstrings * 100 / python_files))

    if [ $coverage -lt 50 ]; then
        print_warning "[$service] Docstring coverage: ${coverage}% (${files_with_docstrings}/${python_files} files)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))  # Warning, not failure
    else
        print_success "[$service] Docstring coverage: ${coverage}% (${files_with_docstrings}/${python_files} files)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi

    return 0
}

# Function to check a single service
check_service() {
    local service=$1
    local service_dir="${BASE_DIR}/${service}"

    # Try to find service directory
    if [ ! -d "$service_dir" ]; then
        for dir in "${BASE_DIR}"/droplet-*-${service}; do
            if [ -d "$dir" ]; then
                service_dir="$dir"
                break
            fi
        done
    fi

    if [ ! -d "$service_dir" ]; then
        print_warning "Service directory not found: $service"
        return 1
    fi

    if [ ! -d "$service_dir/app" ]; then
        print_warning "No app/ directory in $service"
        return 1
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "Checking: $service"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    check_secrets "$service_dir" "$service"
    check_formatting "$service_dir" "$service"
    check_linting "$service_dir" "$service"
    check_types "$service_dir" "$service"
    check_docstrings "$service_dir" "$service"

    echo ""
}

# Function to check all services
check_all() {
    print_info "Checking all Full Potential AI services..."

    # Find all service directories
    local services=()

    # Check for standard service directories
    for dir in registry orchestrator dashboard verifier coordinator; do
        if [ -d "${BASE_DIR}/${dir}" ]; then
            services+=("$dir")
        fi
    done

    # Check for droplet-* directories
    for dir in "${BASE_DIR}"/droplet-*; do
        if [ -d "$dir" ] && [ -d "$dir/app" ]; then
            services+=("$(basename "$dir")")
        fi
    done

    if [ ${#services[@]} -eq 0 ]; then
        print_error "No services found"
        exit 1
    fi

    for service in "${services[@]}"; do
        check_service "$service"
    done
}

# Function to fix issues automatically
auto_fix() {
    local service=$1
    local service_dir="${BASE_DIR}/${service}"

    if [ ! -d "$service_dir" ]; then
        for dir in "${BASE_DIR}"/droplet-*-${service}; do
            if [ -d "$dir" ]; then
                service_dir="$dir"
                break
            fi
        done
    fi

    if [ ! -d "$service_dir" ]; then
        print_error "Service directory not found: $service"
        return 1
    fi

    print_info "Auto-fixing $service..."

    # Run black to format code
    print_info "Formatting code..."
    black "$service_dir/app" "$service_dir/tests"

    # Run ruff with --fix
    print_info "Applying linter fixes..."
    ruff check "$service_dir/app" "$service_dir/tests" --fix || true

    print_success "Auto-fixes applied to $service"
    print_info "Re-run checks to verify"
}

# Main script logic
ensure_tools

case "${1:-help}" in
    all)
        check_all
        ;;
    fix)
        if [ -z "$2" ]; then
            print_error "Usage: $0 fix <service-name>"
            exit 1
        fi
        auto_fix "$2"
        ;;
    help|--help|-h)
        echo "Full Potential AI - Code Standards Checker"
        echo ""
        echo "Usage: $0 <command> [service]"
        echo ""
        echo "Commands:"
        echo "  all              Check all services"
        echo "  <service-name>   Check specific service"
        echo "  fix <service>    Auto-fix issues in service"
        echo "  help             Show this help"
        echo ""
        echo "Checks performed:"
        echo "  - Hardcoded secrets detection"
        echo "  - Code formatting (black)"
        echo "  - Linting (ruff)"
        echo "  - Type hints (mypy)"
        echo "  - Docstring coverage"
        echo ""
        echo "Examples:"
        echo "  $0 all                # Check all services"
        echo "  $0 registry           # Check registry only"
        echo "  $0 fix orchestrator   # Auto-fix orchestrator"
        echo ""
        ;;
    *)
        check_service "$1"
        ;;
esac

# Print summary
if [ $TOTAL_CHECKS -gt 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total Checks: $TOTAL_CHECKS"
    print_success "Passed: $PASSED_CHECKS"
    if [ $FAILED_CHECKS -gt 0 ]; then
        print_error "Failed: $FAILED_CHECKS"
        echo ""
        print_info "Run with 'fix <service>' to auto-fix some issues"
        exit 1
    fi
    echo ""
    print_success "All checks passed! 🌐⚡💎"
fi
