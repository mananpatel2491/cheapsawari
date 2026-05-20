import os
import argparse
from pathlib import Path
from datetime import datetime
try:
    from google import genai
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Required packages not found. Please run: pip install -r requirements.txt")
    import sys
    sys.exit(1)

def select_model(client, model_override=None):
    """Dynamic model selection as per Pattern Registry."""
    if model_override: return model_override
    try:
        available_models = [m for m in client.models.list() if 'generateContent' in m.supported_actions]
        return available_models[0].name
    except Exception: return 'models/gemini-1.5-flash'

def get_context_content(root):
    """Ingests core MD files to provide context to the generator."""
    context = ""
    files_to_read = ["Project_Structure.md", "PATTERNS.md", "GEMINI.md"]
    for filename in files_to_read:
        file_path = root / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                context += f"\n--- {filename} ---\n{f.read()}\n"
    return context

def generate_prompt(intent, requested_model=None, dry_run=False):
    root = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=root / ".env")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
        return

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    model_id = select_model(client, requested_model)
    context = get_context_content(root)

    system_prompt = """
    You are the 'Prompt Architect'. Your task is to turn a simple English intent into a 
    systematic 'Bootstrap Prompt' for a Lead Agent (Gemini).

    STANDING INSTRUCTIONS TO INCLUDE IN THE BOOTSTRAP:
    - After every commit, run `python ./scripts/verify_structure.py`.
    - If it's a backend change, run Bruno validation.
    - No commit is allowed without successful Bruno results unless the owner provides the exception string.
    - Update Project_Structure.md immediately after file changes.

    FOR NEW FEATURES:
    1. Analyze the context provided to see if existing patterns or code can be reused.
    2. If reuse is possible, list the file references.
    3. If brand new, the first line of the prompt must be: 'STATION CHECK: This appears to be a brand-new feature with no reusable components. Confirm to proceed.'

    FOR BUGS:
    1. Convert observations into a systematic troubleshooting hypothesis.
    2. The prompt must require the agent to: Create Hypothesis -> Ask for Confirmation -> Report Findings -> Implementation.

    Output ONLY the final Markdown content for the prompt.
    """

    user_query = f"CONTEXT:\n{context}\n\nUSER INTENT: {intent}"

    print(f"Generating bootstrap prompt using {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id, 
            contents=[system_prompt, user_query]
        )
        prompt_content = response.text.strip()

        # Determine file path
        prompt_dir = root / "bootstrap_prompts"
        prompt_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_{timestamp}.md"
        target_file = prompt_dir / filename

        if dry_run:
            print("\n--- DRY RUN: PROMPT PREVIEW ---")
            print(prompt_content)
            print("--- END PREVIEW ---")
        else:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            print(f"Successfully created bootstrap prompt: {target_file}")
            print(f"Action: Copy the content of this file to start your new session.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a systematic bootstrap prompt from English intent.")
    parser.add_argument("intent", type=str, help="The English description of the feature or bug.")
    parser.add_argument("--model", type=str, help="Specify the Gemini model ID.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the prompt without saving.")
    args = parser.parse_args()
    generate_prompt(args.intent, requested_model=args.model, dry_run=args.dry_run)