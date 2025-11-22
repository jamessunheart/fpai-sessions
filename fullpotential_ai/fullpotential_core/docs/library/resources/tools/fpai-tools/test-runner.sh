#!/bin/bash

# TEST RUNNER
# Blueprint: Foundation Files - CODE_STANDARDS.md (Testing Requirements)
# Purpose: Run tests across all Full Potential AI services
# Usage: ./test-runner.sh [service-name] or ./test-runner.sh all

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
TOTAL_SERVICES=0
PASSED_SERVICES=0
FAILED_SERVICES=0

# Function to run tests for a single service
test_service() {
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

    if [ ! -d "$service_dir/tests" ]; then
        print_warning "No tests/ directory in $service"
        return 1
    fi

    TOTAL_SERVICES=$((TOTAL_SERVICES + 1))

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_info "Testing: $service"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$service_dir"

    # Install dependencies
    if [ -f "requirements.txt" ]; then
        print_info "Installing dependencies..."
        pip install -q -r requirements.txt 2>&1 | grep -v "Requirement already satisfied" || true
    fi

    # Run pytest with coverage
    print_info "Running tests..."

    local test_output
    local exit_code

    if test_output=$(pytest tests/ --cov=app --cov-report=term --cov-report=html -v 2>&1); then
        exit_code=0
    else
        exit_code=$?
    fi

    echo "$test_output"

    # Parse coverage
    local coverage=$(echo "$test_output" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')

    if [ $exit_code -eq 0 ]; then
        print_success "[$service] Tests passed"

        if [ -n "$coverage" ]; then
            if [ ${coverage%.*} -ge 80 ]; then
                print_success "[$service] Coverage: ${coverage}% (meets 80% requirement)"
            else
                print_warning "[$service] Coverage: ${coverage}% (below 80% target)"
            fi
        fi

        PASSED_SERVICES=$((PASSED_SERVICES + 1))
        return 0
    else
        print_error "[$service] Tests failed"
        FAILED_SERVICES=$((FAILED_SERVICES + 1))
        return 1
    fi
}

# Function to test all services
test_all() {
    print_info "Running tests for all Full Potential AI services..."

    # Find all service directories
    local services=()

    # Check for standard service directories
    for dir in registry orchestrator dashboard verifier coordinator; do
        if [ -d "${BASE_DIR}/${dir}" ] && [ -d "${BASE_DIR}/${dir}/tests" ]; then
            services+=("$dir")
        fi
    done

    # Check for droplet-* directories
    for dir in "${BASE_DIR}"/droplet-*; do
        if [ -d "$dir" ] && [ -d "$dir/tests" ]; then
            services+=("$(basename "$dir")")
        fi
    done

    if [ ${#services[@]} -eq 0 ]; then
        print_error "No services with tests found"
        exit 1
    fi

    for service in "${services[@]}"; do
        test_service "$service"
    done
}

# Function to run tests in watch mode
test_watch() {
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
        exit 1
    fi

    print_info "Running tests in watch mode for $service..."
    print_info "Press Ctrl+C to stop"

    cd "$service_dir"
    pytest-watch tests/ -- --cov=app
}

# Function to generate coverage report
generate_coverage_report() {
    print_info "Generating combined coverage report..."

    local report_dir="${BASE_DIR}/coverage-reports"
    mkdir -p "$report_dir"

    # Find all services with coverage data
    local services=()

    for dir in registry orchestrator dashboard verifier coordinator; do
        if [ -d "${BASE_DIR}/${dir}" ] && [ -f "${BASE_DIR}/${dir}/.coverage" ]; then
            services+=("$dir")
        fi
    done

    for dir in "${BASE_DIR}"/droplet-*; do
        if [ -d "$dir" ] && [ -f "$dir/.coverage" ]; then
            services+=("$(basename "$dir")")
        fi
    done

    if [ ${#services[@]} -eq 0 ]; then
        print_warning "No coverage data found. Run tests first."
        return 1
    fi

    # Create HTML report for each service
    for service in "${services[@]}"; do
        local service_dir="${BASE_DIR}/${service}"

        for dir in "${BASE_DIR}"/droplet-*-${service}; do
            if [ -d "$dir" ]; then
                service_dir="$dir"
                break
            fi
        done

        if [ -f "$service_dir/.coverage" ]; then
            print_info "Processing coverage for $service..."
            cd "$service_dir"
            coverage html -d "${report_dir}/${service}"
        fi
    done

    print_success "Coverage reports generated in: $report_dir"
    print_info "Open in browser:"

    for service in "${services[@]}"; do
        echo "  file://${report_dir}/${service}/index.html"
    done
}

# Main script logic
case "${1:-help}" in
    all)
        test_all
        ;;
    watch)
        if [ -z "$2" ]; then
            print_error "Usage: $0 watch <service-name>"
            exit 1
        fi
        test_watch "$2"
        ;;
    coverage)
        generate_coverage_report
        ;;
    help|--help|-h)
        echo "Full Potential AI - Test Runner"
        echo ""
        echo "Usage: $0 <command> [service]"
        echo ""
        echo "Commands:"
        echo "  all               Run tests for all services"
        echo "  <service-name>    Run tests for specific service"
        echo "  watch <service>   Run tests in watch mode"
        echo "  coverage          Generate coverage reports"
        echo "  help              Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 all                  # Test all services"
        echo "  $0 registry             # Test registry only"
        echo "  $0 watch orchestrator   # Watch mode for orchestrator"
        echo "  $0 coverage             # Generate coverage reports"
        echo ""
        ;;
    *)
        test_service "$1"
        ;;
esac

# Print summary
if [ $TOTAL_SERVICES -gt 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total Services: $TOTAL_SERVICES"
    print_success "Passed: $PASSED_SERVICES"

    if [ $FAILED_SERVICES -gt 0 ]; then
        print_error "Failed: $FAILED_SERVICES"
        echo ""
        exit 1
    fi

    echo ""
    print_success "All tests passed! 🌐⚡💎"
fi
