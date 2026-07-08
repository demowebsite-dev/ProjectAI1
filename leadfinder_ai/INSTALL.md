# Installation Guide

Follow these steps to set up LeadFinder AI on your local machine.

## Prerequisites

- **Python 3.12+**
- Basic understanding of terminal/command line

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <your-repo-url>
   cd ProjectAI1
   ```

2. **Set Up a Virtual Environment (Recommended)**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. **Install the Package in Editable Mode**
   This installs all dependencies (`typer`, `rich`, `pydantic`, `playwright`, `scrapling`, `phonenumbers`, `pytest`) as defined in `pyproject.toml`.
   ```bash
   pip install -e .
   ```

4. **Install Playwright Browsers**
   LeadFinder AI uses Playwright to interact with dynamic web pages headlessly. You must install the Chromium browser binaries.
   ```bash
   playwright install chromium
   ```

## Verify Installation

Run the test suite to ensure everything is working correctly. Note: live crawler tests may be skipped unless explicitly enabled.

```bash
python3 -m pytest leadfinder/tests/ --tb=short
```

You can now use the CLI:

```bash
leadfinder --help
```
