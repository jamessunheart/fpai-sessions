#!/bin/bash
#############################################################################
# DEPLOYMENT WRAPPER WITH LEARNING CAPTURE
# Purpose: Wraps deployments to capture learning in the memory system
# Usage: source this file and use deploy_with_learning function
#
# Example:
#   source deploy-with-learning.sh
#   deploy_with_learning "service-name" "v1.0.0" "systemctl restart fpai-service"
#############################################################################

DATA_SERVICE_URL="${DATA_SERVICE_URL:-http://198.54.123.234:8125}"

# Function to capture deployment learning
send_deployment_learning() {
    local service_name="$1"
    local version="$2"
    local success="$3"
    local duration_seconds="$4"
    local error_message="$5"
    
    # Send to memory learning API
    curl -s -X POST "${DATA_SERVICE_URL}/api/learning/deployment" \
        -H "Content-Type: application/json" \
        -d '{
            "service_name": "'"$service_name"'",
            "version": "'"$version"'",
            "success": '"$success"',
            "duration_seconds": '"$duration_seconds"',
            "error_message": '"$(echo "$error_message" | sed 's/"/\\"/g')"'
        }' > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "📚 Deployment learning captured for $service_name"
    fi
}

# Main deployment wrapper
# Usage: deploy_with_learning "service_name" "version" "deploy_command"
deploy_with_learning() {
    local service_name="$1"
    local version="$2"
    local deploy_cmd="$3"
    
    echo "🚀 Starting deployment: $service_name v$version"
    local start_time=$(date +%s)
    
    # Run the deployment command
    local error_output
    error_output=$(eval "$deploy_cmd" 2>&1)
    local exit_code=$?
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Deployment successful: $service_name v$version (${duration}s)"
        send_deployment_learning "$service_name" "$version" "true" "$duration" ""
        return 0
    else
        echo "❌ Deployment failed: $service_name v$version"
        echo "   Error: $error_output"
        send_deployment_learning "$service_name" "$version" "false" "$duration" "$error_output"
        return $exit_code
    fi
}

# Standalone deployment capture (for use after existing deploy scripts)
# Usage: capture_deployment_result "service_name" "version" success_bool duration_seconds [error_message]
capture_deployment_result() {
    local service_name="$1"
    local version="$2"
    local success="$3"
    local duration="$4"
    local error="${5:-}"
    
    send_deployment_learning "$service_name" "$version" "$success" "$duration" "$error"
}

# Export functions
export -f send_deployment_learning
export -f deploy_with_learning
export -f capture_deployment_result

echo "✅ Deployment learning functions loaded"
echo "   Use: deploy_with_learning \"service-name\" \"v1.0\" \"deploy command\""
echo "   Or:  capture_deployment_result \"service-name\" \"v1.0\" true 60"

