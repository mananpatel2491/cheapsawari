# Getting Started with Gemini Code Assist (Auto-Updated)

# Getting Started with Gemini Code Assist

Welcome to the **Gemini Code Assist** guide. Gemini Code Assist is an AI-powered collaborator integrated into your development environment (like VS Code, IntelliJ, or Cloud Workstations) designed to help you write, debug, test, and maintain code faster and more accurately.

This guide covers advanced concepts of Gemini Code Assist, including Agent Mode, Preview models, and how to use custom repository maintenance skills.

---

## 1. Agent Mode vs. Standard Mode

When using Gemini Code Assist, you can interact with the AI in two distinct ways: **Standard Mode** and **Agent Mode**. 

### What is Agent Mode?
**Agent Mode** transforms Gemini from a passive conversational assistant into an active, autonomous collaborator. Instead of just answering questions or generating code blocks for you to copy and paste, the AI acts as an "agent" that can:
* **Analyze your entire workspace:** It searches and reads multiple files across your project to understand the broader context.
* **Formulate a multi-step plan:** It outlines the steps required to solve a complex task (e.g., "Add a new API endpoint, update the database schema, and write unit tests").
* **Modify files directly:** With your permission, it writes, refactors, and edits files across your repository.
* **Run commands and test:** It can execute terminal commands to run builds or tests, read the output, and self-correct if it encounters errors.

### What happens when you do NOT use Agent Mode? (Standard/Chat Mode)
When you do not use Agent Mode, Gemini operates in **Standard Mode**. 
* **Scope is limited:** Gemini behaves as a stateless chat assistant. It primarily looks at your currently open file or highlighted code block.
* **Read-only suggestions:** It generates code suggestions inside the chat panel. You must manually copy, paste, and integrate these changes into your files.
* **No tool execution:** It cannot run terminal commands, compile your code, or automatically debug test failures. It relies entirely on you to act as the intermediary.

| Feature | Standard Mode | Agent Mode |
| :--- | :--- | :--- |
| **Primary Use Case** | Quick questions, code explanations, writing single functions. | Feature implementation, complex refactoring, multi-file changes. |
| **Workspace Access** | Open files and highlighted code. | Deep access to the entire repository and file structure. |
| **Action Capability** | Suggests code in the chat box. | Directly edits files and creates new ones in your workspace. |
| **Self-Correction** | None (you must paste errors back to the chat). | Runs tests/compilers and fixes its own mistakes autonomously. |

---

## 2. Understanding the "Preview" Option

In Gemini Code Assist and Google Cloud, you will often see models or features labeled with a **Preview** tag (e.g., `Gemini 1.5 Pro (Preview)` or `Gemini 2.0 Flash (Preview)`).

### What is a Preview Model/Option?
A **Preview** option represents an early-access, pre-production version of a model, application, or feature. It allows developers to test cutting-edge capabilities before they are finalized for General Availability (GA).

### Key Characteristics of Preview Options:
* **Access to Advanced Capabilities:** Preview models often feature massively expanded context windows (e.g., up to 2 million tokens), faster inference speeds, or improved reasoning capabilities.
* **Not for Production:** Preview models are not recommended for mission-critical, production pipelines as they do not come with standard Enterprise Service Level Agreements (SLAs).
* **Subject to Change:** The behavior, prompt handling, and output style of the model may be actively tuned and updated by Google engineers based on developer feedback.
* **Rate Limits:** Preview features may have lower API rate limits or different pricing structures than GA models.

*Tip: Use **Preview** models during development to test complex code refactoring or large-scale codebase analysis where a massive context window is required.*

---

## 3. Fleet's Maintenance Skills

If your development workflow uses **Fleet** (a specialized codebase toolset integrated with Gemini APIs), you have access to automation scripts called **Maintenance Skills**. Two of the most common maintenance skills are `optimize_changelog.py` and `verify_structure.py`.

These scripts can be executed locally or integrated into your CI/CD pipelines to keep your repository clean, organized, and well-documented.

---

### Skill 1: `optimize_changelog.py`
This script automates the creation and cleanup of your project's `CHANGELOG.md`. It uses Gemini to analyze git logs, remove developer noise (like "fixed typo" or "temp commit"), group changes into logical categories, and generate a polished, user-friendly changelog.

#### How to Use It:
1. **Prepare your environment:** Ensure you have your Gemini API key configured in your terminal:
2. **Run the script:** Navigate to your project root and execute the script via python:
   ```bash
   python ./scripts/optimize_changelog.py --dry-run
   ```
   * *Parameters:*
     * `--model`: (Optional) Specify a specific Gemini model ID.
     * `--dry-run`: (Optional) Preview the optimized table without writing changes.

3. **Review Changes:** The script will leverage Gemini to output a clean markdown structure containing:
   * 🚀 **Features**
   * 🐛 **Bug Fixes**
   * 🧹 **Refactoring & Maintenance**

---

### Skill 2: `verify_structure.py`
This script is a static analysis and structural validation tool. It ensures your repository adheres to predefined organizational standards (e.g., checking that all source files have corresponding test files, verifying configuration file syntax, or checking that directories follow your team's specific architectural patterns).

#### How to Use It:
1. **Define your rules:** Ensure you have a configuration file (usually `structure_rules.json` or `.fleetrules`) in your repository root that defines your expected directory layout.
2. **Run the verification script:**
   ```bash
   python ./scripts/verify_structure.py
   ```
   * *Parameters:*
     * `--dry-run`: Included for fleet consistency; provides a read-only verification.

3. **Interpret the Output:**
   * **Success:** If your codebase matches the expected architecture, the script exits with code `0`.
   * **Failure:** It outputs a list of structural violations (files present on disk but missing from the architecture map).

---
*Last updated via scripts/update_getting_started.py*