import os
import argparse
import re
from pathlib import Path
try:
    from google import genai
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Required packages not found. Please run: pip install -r requirements.txt")
    import sys
    sys.exit(1)

def select_model(client, model_override=None):
    """Dynamic model selection as per Pattern Registry."""
    if model_override:
        return model_override
    try:
        print("Fetching available models...")
        available_models = [
            m for m in client.models.list() 
            if 'generateContent' in m.supported_actions
        ]
        
        if not available_models:
            return 'models/gemini-1.5-flash'

        # For automation, we pick the first one unless interactive
        return available_models[0].name
    except Exception as e:
        print(f"Warning: Could not list models ({e}). Using default.")
        return 'models/gemini-1.5-flash'

def optimize_changelog(requested_model=None, dry_run=False):
    # 1. Setup Environment
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"Error: GOOGLE_API_KEY not found at {env_path}")
        return

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    model_id = select_model(client, requested_model)

    structure_file = root / "Project_Structure.md"
    if not structure_file.exists():
        print(f"Error: {structure_file} not found.")
        return

    # 2. Extract Changelog
    with open(structure_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split content to isolate the Changelog table (usually the last section)
    parts = re.split(r"(## Changelog)", content)
    if len(parts) < 3:
        print("Error: Could not find ## Changelog section in Project_Structure.md")
        return

    preamble = parts[0] + parts[1]
    changelog_table = parts[2].strip()

    # 3. Request Optimization
    prompt = f"""
    You are a technical documentation expert. Below is a Markdown table representing a project changelog.
    Your task is to optimize this table for readability:
    1. Consolidate entries that occur on the same date for the same files/actions.
    2. Ensure the summary is concise but captures the intent of all merged changes.
    3. Maintain the exact Markdown table structure: | Date | Action | Files Affected | Summary |
    4. Return ONLY the optimized table code, including the header and separators. No conversational text.

    CURRENT TABLE:
    {changelog_table}
    """

    print(f"Optimizing changelog using {model_id}...")
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        optimized_table = response.text.strip()

        # Sanitize LLM output (remove triple backticks if present)
        optimized_table = re.sub(r"^```markdown\n|```$", "", optimized_table, flags=re.MULTILINE).strip()

        final_output = f"{preamble}\n\n{optimized_table}\n"

        # 4. Handle Output
        if dry_run:
            print("\n--- DRY RUN: OPTIMIZED TABLE PREVIEW ---")
            print(optimized_table)
            print("\n--- END PREVIEW ---")
        else:
            with open(structure_file, "w", encoding="utf-8") as f:
                f.write(final_output)
            print(f"Successfully updated and optimized {structure_file}")

    except Exception as e:
        print(f"An error occurred during API call: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize the Project_Structure.md changelog using Gemini.")
    parser.add_argument("--model", type=str, help="Specify the Gemini model ID to use.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the changes without writing to file.")
    
    args = parser.parse_args()
    optimize_changelog(requested_model=args.model, dry_run=args.dry_run)
