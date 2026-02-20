# Post Rejections IDX

Automates IDX payment posting for rejection batches using Selenium, with SQLite-based tracking and retry-safe workflows.

## Requirements

- Python 3.13+
- Google Chrome (for Selenium)

## Setup

Create a virtual environment and install dependencies:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install .
```

If you use `uv`, you can also install with:

```cmd
uv sync
```

## Configuration

Environment variables used by `main.py`:

- `IDX_USERNAME` / `IDX_PASSWORD` (required)
- `PUSHBULLET_API_KEY` (optional; enables notifications)
- `ENVIRONMENT` (optional; e.g., `production`)
- `FILE_NAME_OVERRIDE` (optional; override CSV file discovery)

You can place these in a `.env` file at the repo root.

## Usage

Run the automation:

```cmd
run_main.bat
```

Or directly:

```cmd
uv run main.py
```

## Features

- Selenium-driven posting workflow with retries
- SQLite tracking of rejection status
- Log cleanup and structured logging
- Supports multiple date formats for file discovery