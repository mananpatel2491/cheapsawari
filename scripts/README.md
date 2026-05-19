# Agentic Skills (scripts/)

This directory contains maintenance and hygiene scripts designed to be executed by agents to ensure project health and environment consistency.

## Usage
Agents should use Shell Mode to execute these scripts when:
- A file is expected but missing.
- Environment state has drifted.
- Repetitive boilerplate tasks need to be performed.

### Maintenance Workflow
1. **Preview**: Run `python .\scripts\optimize_changelog.py --dry-run` to see how Gemini suggests consolidating duplicate entries.
2. **Apply**: Run `python .\scripts\optimize_changelog.py` to update the `Project_Structure.md`.
3. **Verify**: Run `python .\scripts\verify_structure.py` to ensure project hygiene and changelog integrity.

## Inventory
| Script | Description |
| :--- | :--- |
| `verify_structure.py` | Python-based hygiene script for cross-platform (Win/Mac/Linux) changelog validation. |
| `optimize_changelog.py` | Uses Gemini to consolidate and clean up the Project_Structure.md changelog table. |
