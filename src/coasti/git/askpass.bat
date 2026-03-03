@echo off
REM Git askpass script for Windows
REM GIT_ASKPASS passes the prompt as first argument, but we ignore it
REM and return the token from environment variable

echo %GIT_AUTH_TOKEN%
