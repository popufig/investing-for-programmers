# Investment Research Project

Personal investment research tools based on "Investing for Programmers" (Ch 8-9).

## Skills
Investment research skills in `skills/`. Each subdirectory has a `SKILL.md`:
- `investor-profile` — load as context for all research
- `company-analysis` — 7-step structured analysis with evidence chains
- `bull-bear-debate` — multi-perspective debate framework

## Tools
CLI scripts in `tools/`, run via `python tools/<name>.py`:
- `cluster.py` — S&P 500 K-means clustering (returns × volatility)
- `analyst-targets.py` — analyst price target visualization
- `fetch-financials.py` — financial metrics peer comparison

## Data Flow
- Tools save input snapshots to `data/snapshots/` (timestamped)
- Research output goes to `research/` (git tracked)
- Raw data (earnings PDFs, transcripts) in `data/earnings/` and `data/filings/`

## Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

## Usage
Always load `skills/investor-profile/SKILL.md` when doing investment analysis.
