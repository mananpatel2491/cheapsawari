import os
import argparse
from pathlib import Path
try:
    from google import genai
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Required packages not found.")
    print("Please run: pip install -r requirements.txt")
    import sys
    sys.exit(1)

def select_model(client, model_override=None):
    """Lists available models and lets the user select one."""
    if model_override:
        print(f"Using model override: {model_override}")
        return model_override

    print("Fetching available models...")
    try:
        # Filter for models that support generating content
        available_models = [
            m for m in client.models.list() 
            if 'generateContent' in m.supported_actions
        ]
        
        if not available_models:
            return 'gemini-1.5-flash'  # Fallback

        print("\nAvailable Gemini Models:")
        for i, m in enumerate(available_models):
            print(f" [{i}] {m.name} ({m.display_name})")
        
        selection = input(f"\nSelect a model index [default 0: {available_models[0].name}]: ").strip()
        index = int(selection) if selection.isdigit() and int(selection) < len(available_models) else 0
        return available_models[index].name
    except Exception as e:
        print(f"Warning: Could not list models ({e}). Using default.")
        return 'models/gemini-1.5-flash'

def update_docs(requested_model=None, dry_run=False):
    # 1. Load environment variables from .env file if it exists
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    load_dotenv(dotenv_path=env_path)

    # 2. Setup API Key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"Error: GOOGLE_API_KEY not found in environment or at {env_path}")
        print("Please ensure your API key is set before running.")
        return

    # Force 'v1' API version to avoid 404s common in the v1beta endpoint
    # for specific model aliases like 'gemini-1.5-flash'.
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    model_id = select_model(client, requested_model)

    # 3. Define the prompt
    prompt = """
    Explain how to use Gemini Code Assist. 
    Specifically cover: 
    1. What is Agent mode and what happens when I do not use it?
    2. What is the Preview option in the context of code applications and models?
    3. How to use the Fleet's Maintenance Skills. Note that optimize_changelog.py and verify_structure.py both support standard --model and --dry-run arguments.
    Format the output as a clean Markdown document suitable for a 'Getting Started' guide.
    """

    print("Querying Gemini API for latest documentation...")
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        content = response.text

        # 4. Determine file path
        target_file = root / "GEMINI_Getting_Started.md"

        output_content = f"# Getting Started with Gemini Code Assist (Auto-Updated)\n\n{content}\n\n---\n*Last updated via scripts/update_getting_started.py*"

        # 5. Write the file
        if dry_run:
            print("\n--- DRY RUN: OUTPUT PREVIEW ---")
            print(output_content)
            print("--- END PREVIEW ---")
        else:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(output_content)
            print(f"Successfully updated {target_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Gemini onboarding docs via API.")
    parser.add_argument("--model", type=str, help="Specify the Gemini model ID to use (bypasses selection).")
    parser.add_argument("--dry-run", action="store_true", help="Preview the output without writing to the file.")
    
    args = parser.parse_args()
    update_docs(requested_model=args.model, dry_run=args.dry_run)