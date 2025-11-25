#!/bin/bash
#
# 🔍 APPRENTICE PRE-FLIGHT CHECK
# Run this in your repository BEFORE submitting to Full Potential OS
#
# This script validates that your submission meets minimum requirements
# and catches common issues early.
#
# Usage:
#   cd your-repo/
#   curl -sSL https://fullpotential.ai/preflight.sh | bash
#   # OR if you have the script locally:
#   ./apprentice-preflight-check.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0
CHECKS=0

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔍 APPRENTICE PRE-FLIGHT CHECK - Full Potential OS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📋 Validating submission requirements..."
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((CHECKS++))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo -e "   ${RED}→${NC} $2"
    ((ERRORS++))
    ((CHECKS++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    echo -e "   ${YELLOW}→${NC} $2"
    ((WARNINGS++))
    ((CHECKS++))
}

# Check 1: Git repository
echo "Checking: Git repository..."
if [ -d ".git" ]; then
    check_pass "Git repository detected"
else
    check_fail "Not a git repository" "Initialize with: git init"
fi

# Check 2: Tests exist
echo "Checking: Tests..."
if [ -d "tests" ] || [ -d "test" ] || find . -maxdepth 2 -name "test_*.py" -o -name "*_test.py" -o -name "*.test.js" -o -name "*.test.ts" | grep -q .; then
    check_pass "Test files/directory found"
    
    # Try to run tests
    if [ -f "requirements.txt" ] && command -v pytest &> /dev/null; then
        echo "   Running Python tests..."
        if pytest --collect-only &> /dev/null; then
            if pytest -v 2>&1 | tee /tmp/pytest_output.txt; then
                check_pass "Tests executed successfully"
            else
                check_fail "Tests failed" "Fix failing tests before submitting"
            fi
        else
            check_warn "Could not collect tests" "Ensure pytest can discover your tests"
        fi
    elif [ -f "package.json" ] && command -v npm &> /dev/null; then
        echo "   Running Node.js tests..."
        if npm test &> /dev/null; then
            check_pass "Tests executed successfully"
        else
            check_warn "Tests failed or no test script defined" "Ensure 'npm test' works"
        fi
    else
        check_warn "Could not run tests automatically" "Ensure tests pass in your environment"
    fi
else
    check_fail "No tests found" "Add tests in 'tests/' directory or as test_*.py files"
fi

# Check 3: README exists
echo "Checking: Documentation..."
if [ -f "README.md" ]; then
    check_pass "README.md found"
    
    # Check README has meaningful content
    readme_lines=$(wc -l < README.md)
    if [ "$readme_lines" -lt 10 ]; then
        check_warn "README.md is very short ($readme_lines lines)" "Add more documentation about setup, usage, and examples"
    fi
else
    check_fail "No README.md found" "Create README.md with setup instructions and usage examples"
fi

# Check 4: Dependencies specified
echo "Checking: Dependencies..."
if [ -f "requirements.txt" ] || [ -f "package.json" ] || [ -f "go.mod" ] || [ -f "Cargo.toml" ]; then
    check_pass "Dependency file found"
    
    # Check for version pinning
    if [ -f "requirements.txt" ]; then
        if grep -q "==" requirements.txt; then
            check_pass "Python dependencies are pinned"
        else
            check_warn "Python dependencies not pinned" "Pin versions with '==' for reproducibility"
        fi
    fi
else
    check_fail "No dependency file found" "Add requirements.txt (Python), package.json (Node), etc."
fi

# Check 5: No hardcoded secrets
echo "Checking: Security - Hardcoded secrets..."
SECRET_PATTERNS="API_KEY|SECRET_KEY|PASSWORD|TOKEN|PRIVATE_KEY|AWS_ACCESS|DB_PASSWORD"
if grep -rI --exclude-dir={.git,venv,node_modules,__pycache__,.pytest_cache} \
     --exclude="*.{log,pyc}" \
     -E "$SECRET_PATTERNS" . 2>/dev/null | grep -v "# nosec" | grep -v "example" | grep -q .; then
    check_fail "Possible hardcoded secrets detected" "Move secrets to environment variables or .env files"
    echo "   ${YELLOW}Matches:${NC}"
    grep -rI --exclude-dir={.git,venv,node_modules,__pycache__,.pytest_cache} \
         --exclude="*.{log,pyc}" \
         -E "$SECRET_PATTERNS" . 2>/dev/null | grep -v "# nosec" | grep -v "example" | head -5 | sed 's/^/     /'
else
    check_pass "No obvious hardcoded secrets detected"
fi

# Check 6: .gitignore present
echo "Checking: .gitignore..."
if [ -f ".gitignore" ]; then
    check_pass ".gitignore found"
else
    check_warn "No .gitignore found" "Add .gitignore to exclude venv/, __pycache__/, .env, etc."
fi

# Check 7: Code quality (basic)
echo "Checking: Code quality..."
if command -v flake8 &> /dev/null && [ -f "requirements.txt" ]; then
    if flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics &> /dev/null; then
        check_pass "No critical Python syntax errors"
    else
        check_warn "Python syntax/import errors detected" "Run: flake8 . --select=E9,F63,F7,F82"
    fi
elif command -v eslint &> /dev/null && [ -f "package.json" ]; then
    if npx eslint . &> /dev/null; then
        check_pass "No critical JavaScript errors"
    else
        check_warn "JavaScript linting issues detected" "Run: npx eslint ."
    fi
else
    check_warn "Could not run linter" "Install flake8 (Python) or eslint (Node) for code quality checks"
fi

# Check 8: License file
echo "Checking: License..."
if [ -f "LICENSE" ] || [ -f "LICENSE.md" ] || [ -f "LICENSE.txt" ]; then
    check_pass "License file found"
else
    check_warn "No LICENSE file found" "Add a LICENSE file if this will be public/open-source"
fi

# Check 9: Clean git state
echo "Checking: Git state..."
if [ -d ".git" ]; then
    if [ -z "$(git status --porcelain)" ]; then
        check_pass "Working directory is clean (all changes committed)"
    else
        check_warn "Uncommitted changes detected" "Commit all changes before submitting"
        git status --short | head -5 | sed 's/^/     /'
    fi
fi

# Check 10: Reasonable repo size
echo "Checking: Repository size..."
if [ -d ".git" ]; then
    repo_size=$(du -sh . 2>/dev/null | cut -f1)
    repo_size_mb=$(du -sm . 2>/dev/null | cut -f1)
    
    if [ "$repo_size_mb" -lt 100 ]; then
        check_pass "Repository size is reasonable ($repo_size)"
    elif [ "$repo_size_mb" -lt 500 ]; then
        check_warn "Repository is large ($repo_size)" "Consider using .gitignore to exclude build artifacts, data files, etc."
    else
        check_fail "Repository is very large ($repo_size)" "Remove large files, use Git LFS, or .gitignore build artifacts"
    fi
fi

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 SUMMARY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Total checks: $CHECKS"
echo -e "${RED}Errors:       $ERRORS${NC}"
echo -e "${YELLOW}Warnings:     $WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ PERFECT! All checks passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "🎉 Your submission is ready!"
    echo ""
    echo "📤 Next steps:"
    echo "   1. Push your code to GitHub (or GitLab, etc.)"
    echo "   2. Share the repository URL with the system"
    echo "   3. Wait for automated review and integration"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  ACCEPTABLE with warnings${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "✅ Your submission meets minimum requirements."
    echo "⚠️  However, there are $WARNINGS warning(s) that should be addressed for best practices."
    echo ""
    echo "📤 You can submit now, but consider fixing warnings for higher quality."
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ SUBMISSION NOT READY${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Please fix the $ERRORS error(s) above before submitting."
    echo ""
    echo "💡 Common fixes:"
    echo "   - Add tests in a 'tests/' directory"
    echo "   - Create README.md with setup instructions"
    echo "   - Add requirements.txt or package.json"
    echo "   - Remove hardcoded secrets (use environment variables)"
    echo ""
    exit 1
fi

