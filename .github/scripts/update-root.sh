#!/bin/bash

# Exit on error
set -e

# Required environment variables check
if [ -z "$ROOT_REPO_TOKEN" ] || [ -z "$ROOT_REPO" ] || [ -z "$SERVICE_NAME" ]; then
    echo "Error: Required environment variables not set"
    echo "Please set: ROOT_REPO_TOKEN, ROOT_REPO, SERVICE_NAME"
    exit 1
fi

# Configure git
git config --global user.name "GitHub Actions"
git config --global user.email "actions@github.com"

# Clone the root repository
git clone https://x-access-token:${ROOT_REPO_TOKEN}@github.com/${ROOT_REPO}.git root-project
cd root-project

# Create a new branch
BRANCH="chore/update-${SERVICE_NAME}-$(date +%s)"
git checkout -b $BRANCH

# Update the submodule
git submodule update --init services/${SERVICE_NAME}
cd services/${SERVICE_NAME}
git fetch origin main
git checkout origin/main
cd ../..

# Commit the change
git add services/${SERVICE_NAME}
git commit -m "chore: update ${SERVICE_NAME} service to latest version"

# Push the branch
git push origin $BRANCH

# Create PR using GitHub API
PR_RESPONSE=$(curl -X POST \
  -H "Authorization: token ${ROOT_REPO_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/${ROOT_REPO}/pulls \
  -d "{
    \"title\": \"Update ${SERVICE_NAME} service to latest version\",
    \"body\": \"This PR was automatically created to update the ${SERVICE_NAME} service submodule to its latest version.\n\nChanges included in this update can be viewed at: \${GITHUB_SERVER_URL}/\${GITHUB_REPOSITORY}/commit/\${GITHUB_SHA}\",
    \"head\": \"${BRANCH}\",
    \"base\": \"main\"
  }")

echo "Pull request created: $(echo $PR_RESPONSE | jq -r .html_url)" 