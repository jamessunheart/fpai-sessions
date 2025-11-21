#!/bin/bash

# Audit all services for standard structure

echo "# SERVICES STRUCTURE AUDIT"
echo "================================"
echo ""

cd /Users/jamessunheart/Development/SERVICES

for service_dir in */; do
    service="${service_dir%/}"
    echo "## $service"

    # Check README
    if [ -f "$service/README.md" ]; then
        echo "  README.md:    ✅"
    else
        echo "  README.md:    ❌ MISSING"
    fi

    # Check SPEC
    spec_found=false
    for spec_file in "$service"/*SPEC*.md "$service"/*spec*.md; do
        if [ -f "$spec_file" ]; then
            echo "  SPEC:         ✅ $(basename "$spec_file")"
            spec_found=true
            break
        fi
    done
    if [ "$spec_found" = false ]; then
        echo "  SPEC:         ❌ MISSING"
    fi

    # Check Dockerfile
    if [ -f "$service/Dockerfile" ]; then
        echo "  Dockerfile:   ✅"
    else
        echo "  Dockerfile:   ❌ MISSING"
    fi

    # Check Tests
    test_found=false
    if [ -d "$service/test" ] || [ -d "$service/tests" ]; then
        echo "  Tests:        ✅ (directory)"
        test_found=true
    else
        for test_file in "$service"/test_*.py; do
            if [ -f "$test_file" ]; then
                echo "  Tests:        ✅ $(basename "$test_file")"
                test_found=true
                break
            fi
        done
    fi
    if [ "$test_found" = false ]; then
        echo "  Tests:        ❌ MISSING"
    fi

    # Check app directory
    if [ -d "$service/app" ]; then
        echo "  app/:         ✅"
    else
        echo "  app/:         ❌ MISSING"
    fi

    # Check requirements.txt
    if [ -f "$service/requirements.txt" ]; then
        echo "  requirements: ✅"
    else
        echo "  requirements: ❌ MISSING"
    fi

    echo ""
done

echo "================================"
echo "Audit complete!"
