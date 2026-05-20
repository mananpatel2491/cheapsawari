# Agentic-Vibe-Fleet

A production-grade vibe coding framework designed to orchestrate an army of autonomous agents. It transforms high-level English intent into scalable software using a multi-LLM stack (Claude, Gemini, and local Ollama) while maintaining strict architectural integrity through a Project Constitution.

## 🏗️ Core Roles
- **The Director (User)**: Responsible for high-level intent, architectural arbitration, and final review.
- **The Lead Agent (Gemini)**: Responsible for autonomous reasoning, implementation planning, and execution using a massive 1M+ token context window.

## 🚀 The Vibe Coding Workflow
To maintain quality while coding via English intent:
1. **Generate Plan**: Run `python ./scripts/generate_bootstrap_prompt.py "Your intent here"`.
2. **Start Session**: Copy the generated prompt from `bootstrap_prompts/` into a new Gemini session.
3. **Execute**: Let the Lead Agent implement, ensuring it follows the **Standing Instructions** provided in the prompt.
4. **Maintain**: Run the **Maintenance Workflows** (below) after every feature to prevent context rot.

## 🛠️ Getting Started
1. **Install Dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**: Create a `.env` file in the root with your `GOOGLE_API_KEY`.
3. **Onboarding**: Run the documentation script to generate your personalized guide:
   ```bash
   python ./scripts/update_getting_started.py
   ```

## 🧹 Maintenance Workflows
Use the following **Agentic Skills** to ensure project hygiene:

- **Verify Structure**: `python ./scripts/verify_structure.py` (Ensures filesystem matches the Architecture Map).
- **Optimize Changelog**: `python ./scripts/optimize_changelog.py` (Consolidates logs for readability).
- **Refresh Docs**: `python ./scripts/update_getting_started.py` (Updates the onboarding guide).

---
*Refer to `Project_Structure.md` for the full functional map of the codebase.*
