#!/bin/bash
# Rewrite all commits authored by deploy@mypy-tutor.com to tega.com.ng@gmail.com
git filter-branch --env-filter '
OLD_EMAIL="deploy@mypy-tutor.com"
CORRECT_NAME="Sir. Tega"
CORRECT_EMAIL="tega.com.ng@gmail.com"
if [ "$GIT_COMMITTER_EMAIL" = "$OLD_EMAIL" ]; then
    export GIT_COMMITTER_NAME="$CORRECT_NAME"
    export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
fi
if [ "$GIT_AUTHOR_EMAIL" = "$OLD_EMAIL" ]; then
    export GIT_AUTHOR_NAME="$CORRECT_NAME"
    export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags
