#!/bin/bash
#
# CHECK-IN Script for ES Inventory Hub
# Automated git commit and tag workflow with version management
#

set -euo pipefail

# Configuration
REPO_ROOT="/opt/es-inventory-hub"
README_FILE="${REPO_ROOT}/README.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[CHECK-IN]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to get the next version number
get_next_version() {
    local current_version
    local major minor patch
    
    # Get the latest tag, if any
    current_version=$(git tag --sort=-version:refname | head -1 || echo "")
    
    if [ -z "$current_version" ]; then
        echo "v1.0.0"
        return
    fi
    
    # Remove 'v' prefix and split into components
    version_number="${current_version#v}"
    echo "$version_number" | IFS='.' read -r major minor patch
    
    # For now, increment patch version by default
    # In the future, this could be made configurable
    patch=$((patch + 1))
    
    echo "v${major}.${minor}.${patch}"
}

# Function to update version in README
update_readme_version() {
    local new_version="$1"
    
    if grep -q "Current Version" "$README_FILE"; then
        # Update existing version line
        sed -i "s/\*\*Current Version\*\*: v[0-9]\+\.[0-9]\+\.[0-9]\+/\*\*Current Version\*\*: $new_version/" "$README_FILE"
        sed -i "s/## *Current Version (v[0-9]\+\.[0-9]\+\.[0-9]\+)/## Current Version ($new_version)/" "$README_FILE"
    else
        # Add version line after the overview section
        sed -i '/## Overview/a\\n**Current Version**: '"$new_version"' (stable)\n' "$README_FILE"
    fi
}

# Function to get git status summary
get_git_status_summary() {
    local status_output
    status_output=$(git status --porcelain)
    
    if [ -z "$status_output" ]; then
        echo "No changes detected"
        return 1
    fi
    
    echo "Changes detected:"
    echo "$status_output" | while read -r line; do
        local status="${line:0:2}"
        local file="${line:3}"
        case "$status" in
            "??") echo "  + New file: $file" ;;
            " M") echo "  ~ Modified: $file" ;;
            "M ") echo "  ~ Modified: $file" ;;
            " D") echo "  - Deleted: $file" ;;
            "D ") echo "  - Deleted: $file" ;;
            "A ") echo "  + Added: $file" ;;
            "R ") echo "  > Renamed: $file" ;;
            *) echo "  ? $status $file" ;;
        esac
    done
}

# Function to generate commit message
generate_commit_message() {
    local version="$1"
    local status_summary="$2"
    
    cat << EOF
Release $version - ES Inventory Hub Updates

$status_summary

This release includes all recent changes and improvements to the
ES Inventory Hub project, properly versioned and tagged for
production deployment and rollback capability.
EOF
}

# Function to generate tag message
generate_tag_message() {
    local version="$1"
    local status_summary="$2"
    
    cat << EOF
ES Inventory Hub Release $version

CHANGES IN THIS RELEASE:
$status_summary

RELEASE NOTES:
- All changes have been committed and versioned
- README.md updated with current version number
- Production-ready release with full documentation
- Comprehensive git history maintained for rollback capability

PROJECT COMPONENTS:
- Ninja collector with UPSERT functionality
- PostgreSQL database schema and migrations
- Shared utilities and configuration management
- Cron-friendly daily collection scripts
- Comprehensive documentation and operations guides

For detailed change history, see: git log --oneline $version^..$version
EOF
}

# Main execution
main() {
    print_status "Starting CHECK-IN process for ES Inventory Hub..."
    
    # Change to repository root
    cd "$REPO_ROOT"
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
    
    # Get git status
    print_info "Checking repository status..."
    if ! status_summary=$(get_git_status_summary); then
        print_warning "No changes detected in repository"
        print_info "Repository is clean, no CHECK-IN needed"
        exit 0
    fi
    
    print_info "$status_summary"
    
    # Get next version
    next_version=$(get_next_version)
    print_info "Next version will be: $next_version"
    
    # Stage all changes
    print_status "Staging all changes..."
    git add .
    
    # Update README with new version
    print_status "Updating README.md with version $next_version..."
    update_readme_version "$next_version"
    git add "$README_FILE"
    
    # Generate commit message
    commit_message=$(generate_commit_message "$next_version" "$status_summary")
    
    # Commit changes
    print_status "Committing changes..."
    git commit -m "$commit_message"
    
    # Generate tag message
    tag_message=$(generate_tag_message "$next_version" "$status_summary")
    
    # Create tag
    print_status "Creating tag $next_version..."
    git tag -a "$next_version" -m "$tag_message"
    
    # Push changes and tags
    print_status "Pushing to remote repository..."
    git push origin "$(git branch --show-current)"
    git push origin "$next_version"
    
    # Success summary
    echo
    print_status "CHECK-IN COMPLETE! ✅"
    echo
    echo -e "${GREEN}Tag Used:${NC} $next_version"
    echo
    echo -e "${GREEN}Changes Committed:${NC}"
    echo "$status_summary"
    echo
    echo -e "${GREEN}Files Modified:${NC}"
    git show --name-only --format="" "$next_version" | sed 's/^/- /'
    echo
    echo -e "${GREEN}The changes have been successfully committed and pushed to the remote repository${NC}"
    echo -e "${GREEN}All detailed revision notes are preserved in Git tag messages and commit history${NC}"
    echo
    echo -e "${BLUE}View this release:${NC} git show $next_version"
    echo -e "${BLUE}View commit log:${NC} git log --oneline -10"
}

# Run main function
main "$@"
