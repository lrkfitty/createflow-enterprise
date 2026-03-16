# AI Content Creator Workflow

This project implements a 3-layer architecture for reliable AI-driven workflows.

## Architecture

1.  **Directives (`directives/`)**: SOPs and instructions in Markdown.
2.  **Orchestration (Agent)**: The AI agent reads directives and runs tools.
3.  **Execution (`execution/`)**: Deterministic Python scripts.

## Setup

1.  Copy `.env.example` to `.env` and fill in your values.
2.  Ensure `credentials.json` is present if using Google APIs.
3.  Scripts are located in `execution/`.
