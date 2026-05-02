# Agent Dropbox — OpenClaw Agent Container
#
# This Dockerfile creates an agent environment that knows about
# synced files from Agent Dropbox. The synced files are mounted
# at /shared_data via a volume mount from the host.
#
# Build:
#   docker build -t agent-dropbox-agent .
#
# Run (assuming S3 bucket is mounted on host at /mnt/s3-bucket):
#   docker run -v /mnt/s3-bucket:/shared_data agent-dropbox-agent
#
# To use Hermes Agent instead, change the base image:
#   FROM ghcr.io/nousresearch/hermes-agent:latest

FROM ghcr.io/openclaw/openclaw:latest

COPY AGENT.md /workspace/AGENT.md
COPY MEMORY.md /workspace/MEMORY.md

VOLUME /shared_data

WORKDIR /workspace
