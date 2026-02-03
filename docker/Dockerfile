FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS base

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    vim \
    nano

RUN git config --global init.defaultBranch main \
    git config --global user.email "you@example.com" \
    git config --global user.name "Your Name"
