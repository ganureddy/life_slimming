#!/bin/bash

# Define the three directories with their corresponding repositories
DIR1="/home/erpnext/bench/frappe-bench/apps/"
DIR2="/home/erpnext/bench/healthcare-bench/apps/"
DIR3="/home/erpnext/bench/ezy-bench/apps/"
REPO1="life_slimming"
REPO2="healthcare"
REPO3="version2_app"

# Define the environment tags
ENV_PROD="stable"
ENV_UAT="uat"
ENV_TEST="test"

# Loop through each directory and check if any repo has been tagged for release
#for dir in "$DIR1" "$DIR2" "$DIR3"; do
    cd "$DIR1"
#    for repo in "$REPO1" "$REPO2" "$REPO3"; do
        cd "$REPO1"
        if git tag --points-at HEAD | grep -qE "^$ENV_PROD"; then
            # Checkout the tagged release
            git fetch --tags
            git checkout tags/$(git describe --tags --abbrev=0 --match="$ENV_PROD")
#            bench migrate
        else
        cd "$DIR2"
        cd "$REPO2"
         git tag --points-at HEAD | grep -qE "^$ENV_UAT"; then
            # Checkout the tagged release
            git fetch --tags
            git checkout tags/$(git describe --tags --abbrev=0 --match="$ENV_UAT")
        elif
        cd "$DIR3"
        cd "$REPO3"
          git tag --points-at HEAD | grep -qE "^$ENV_TEST"; then
            # Checkout the tagged release
            git fetch --tags
            git checkout tags/$(git describe --tags --abbrev=0 --match="$ENV_TEST")
        fi
#        cd ..
#    done
#done
