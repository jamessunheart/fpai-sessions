#!/bin/bash

# LOCAL DEVELOPMENT LAUNCHER
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Section 9 (Operational Topology)
# Purpose: Start all Full Potential AI services in development mode
# Usage: ./local-dev.sh [service-name] or ./local-dev.sh all

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

# Service configuration
declare -A SERVICES=(
    ["registry"]="8001"
    ["orchestrator"]="8010"
    ["dashboard"]="8002"
    ["proxy-manager"]="8003"
    ["verifier"]="8008"
    ["coordinator"]="8011"
)

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find service directory
find_service_dir() {
    local service=$1

    # Try exact name first
    if [ -d "${BASE_DIR}/${service}" ]; then
        echo "${BASE_DIR}/${service}"
        return 0
    fi

    # Try with droplet prefix
    for dir in "${BASE_DIR}"/droplet-*-${service}; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done

    return 1
}

# Function to start a single service
start_service() {
    local service=$1
    local port=${SERVICES[$service]}

    if [ -z "$port" ]; then
        print_error "Unknown service: $service"
        return 1
    fi

    print_info "Starting $service on port $port..."

    # Find service directory
    service_dir=$(find_service_dir "$service")

    if [ -z "$service_dir" ]; then
        print_warning "Service directory not found for $service"
        print_info "Available services:"
        for s in "${!SERVICES[@]}"; do
            echo "  - $s"
        done
        return 1
    fi

    # Check if port is already in use
    if check_port $port; then
        print_warning "$service is already running on port $port"
        return 0
    fi

    # Check if app/main.py exists
    if [ ! -f "${service_dir}/app/main.py" ]; then
        print_error "No app/main.py found in ${service_dir}"
        return 1
    fi

    # Load .env if exists
    if [ -f "${service_dir}/.env" ]; then
        export $(cat "${service_dir}/.env" | grep -v '^#' | xargs)
    fi

    # Start service in background
    cd "${service_dir}"

    print_info "Installing dependencies for $service..."
    pip install -q -r requirements.txt 2>&1 | grep -v "Requirement already satisfied" || true

    print_info "Launching $service..."
    PORT=$port uvicorn app.main:app --host 0.0.0.0 --port $port --reload > "/tmp/fpai-${service}.log" 2>&1 &

    local pid=$!
    echo $pid > "/tmp/fpai-${service}.pid"

    # Wait a moment and check if it started
    sleep 2

    if ps -p $pid > /dev/null; then
        print_success "$service started on port $port (PID: $pid)"
        print_info "Logs: /tmp/fpai-${service}.log"
        return 0
    else
        print_error "$service failed to start"
        print_info "Check logs: /tmp/fpai-${service}.log"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service=$1
    local pid_file="/tmp/fpai-${service}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            print_info "Stopping $service (PID: $pid)..."
            kill $pid
            rm "$pid_file"
            print_success "$service stopped"
        else
            print_warning "$service was not running"
            rm "$pid_file"
        fi
    else
        print_warning "No PID file found for $service"
    fi
}

# Function to show status
show_status() {
    echo ""
    print_info "Full Potential AI - Service Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        local pid_file="/tmp/fpai-${service}.pid"

        printf "%-20s Port %-6s " "$service" "$port"

        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${GREEN}🟢 Running (PID: $pid)${NC}"
            else
                echo -e "${RED}🔴 Stopped (stale PID)${NC}"
                rm "$pid_file"
            fi
        else
            if check_port $port; then
                echo -e "${YELLOW}🟡 Running (unknown PID)${NC}"
            else
                echo -e "⚫ Not running"
            fi
        fi
    done

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Function to stop all services
stop_all() {
    print_info "Stopping all services..."

    for service in "${!SERVICES[@]}"; do
        stop_service "$service"
    done

    print_success "All services stopped"
}

# Function to start all services
start_all() {
    print_info "Starting all Full Potential AI services..."
    echo ""

    # Start in dependency order
    # Phase 1: Foundation
    start_service "registry"
    sleep 2
    start_service "orchestrator"
    sleep 2

    # Phase 2: Infrastructure
    start_service "dashboard"
    start_service "proxy-manager"
    start_service "verifier"

    # Phase 3: Automation
    start_service "coordinator"

    echo ""
    show_status

    print_info "Development servers running!"
    echo ""
    echo "URLs:"
    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        echo "  $service: http://localhost:$port"
    done
    echo ""
    print_info "To stop all services: ./local-dev.sh stop"
    print_info "To view logs: tail -f /tmp/fpai-*.log"
}

# Function to tail logs
tail_logs() {
    if [ -z "$1" ]; then
        print_info "Tailing all service logs..."
        tail -f /tmp/fpai-*.log
    else
        local service=$1
        if [ -f "/tmp/fpai-${service}.log" ]; then
            print_info "Tailing logs for $service..."
            tail -f "/tmp/fpai-${service}.log"
        else
            print_error "No log file found for $service"
            exit 1
        fi
    fi
}

# Main script logic
case "${1:-help}" in
    all)
        start_all
        ;;
    start)
        if [ -z "$2" ]; then
            print_error "Usage: $0 start <service-name>"
            exit 1
        fi
        start_service "$2"
        ;;
    stop)
        if [ -z "$2" ]; then
            stop_all
        else
            stop_service "$2"
        fi
        ;;
    restart)
        if [ -z "$2" ]; then
            stop_all
            sleep 2
            start_all
        else
            stop_service "$2"
            sleep 2
            start_service "$2"
        fi
        ;;
    status)
        show_status
        ;;
    logs)
        tail_logs "$2"
        ;;
    help|--help|-h)
        echo "Full Potential AI - Local Development Launcher"
        echo ""
        echo "Usage: $0 <command> [service]"
        echo ""
        echo "Commands:"
        echo "  all              Start all services"
        echo "  start <service>  Start a specific service"
        echo "  stop [service]   Stop service(s) (all if no service specified)"
        echo "  restart [service] Restart service(s)"
        echo "  status           Show status of all services"
        echo "  logs [service]   Tail logs (all or specific service)"
        echo "  help             Show this help message"
        echo ""
        echo "Services:"
        for service in "${!SERVICES[@]}"; do
            printf "  %-20s Port %s\n" "$service" "${SERVICES[$service]}"
        done
        echo ""
        echo "Examples:"
        echo "  $0 all                  # Start all services"
        echo "  $0 start registry       # Start registry only"
        echo "  $0 stop                 # Stop all services"
        echo "  $0 restart orchestrator # Restart orchestrator"
        echo "  $0 status               # Show service status"
        echo "  $0 logs registry        # Tail registry logs"
        echo ""
        ;;
    *)
        # Default: try to start the named service
        if [[ -n "${SERVICES[$1]}" ]]; then
            start_service "$1"
        else
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
        fi
        ;;
esac
