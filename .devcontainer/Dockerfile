FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /usr/local/bin/
COPY --from=oven/bun:1.4.0 /usr/local/bin/bun /usr/local/bin/bun
RUN ln -s /usr/local/bin/bun /usr/local/bin/bunx
