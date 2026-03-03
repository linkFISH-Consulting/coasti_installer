#!/bin/sh
# Git askpass script for Unix
# GIT_ASKPASS passes the prompt as first argument, but we ignore it
# and return the token from environment variable
exec echo "$GIT_AUTH_TOKEN"
