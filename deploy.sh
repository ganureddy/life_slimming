#!/bin/bash

# Define the stable, test, and uat tag names
repo1_tag="testing"
repo2_tag="uat"
repo3_tag="stable"

# Set the working directory for each repo
repo1_dir="/home/erpnext/bench/frappe-bench/apps/life_slimming"
repo2_dir="/home/erpnext/bench/frappe-bench/apps/life_slimming"
repo3_dir="/home/erpnext/bench/frappe-bench/apps/life_slimming"

# Get the current tag name
current_tag=$(git describe --tags --exact-match HEAD 2>/dev/null)

current_branch=$(git rev-parse --abbrev-ref HEAD)

# Check if the current tag is a stable tag
if [[ "$current_tag" == "$repo3_tag" ]]; then
    echo "Checking out $repo3_tag in repo3"
    cd "$repo3_dir"
    git pull ref/tags/$repo3_tag/*
# Check if the current tag is a test tag
elif [[ "$current_tag" == "$repo2_tag" ]]; then
    echo "Checking out $repo2_tag in repo2"
    cd "$repo2_dir"
    git checkout "$repo2_tag"
# Check if the current tag is a uat tag
elif [[ "$current_tag" == "$repo3_tag" ]]; then
    echo "Checking out $repo3_tag in repo3"
    cd "$repo3_dir"
    git checkout "$repo3_tag"
# If no tag name matches, print an error message
else
    echo "Error: Unknown tag name '$current_tag'"
fi
