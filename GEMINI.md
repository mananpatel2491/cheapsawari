This document serves as the long-term memory and central nervous system for all Gemini-led sessions within the Agentic Vibe Fleet framework. It codifies five hard-won lessons into non-negotiable operating procedures to ensure architectural integrity and prevent "context rot" [790, 811, conversation history].

Role Definition
- The Director (User): Responsible for high-level intent, architectural arbitration, and final review
- The Lead Agent (Gemini): Responsible for autonomous reasoning, implementation planning, and error-free execution using the 1M token context window [130, 993, conversation history].

--------------------------------------------------------------------------------
The Five Core Lessons
1. Context-First Architecture Map
- Rule: Before proposing any changes, the agent must read Project Structure.md [790, conversation history].
- Purpose: Use functional descriptions of folders and files to identify how to introduce features, simplify design, and trace security issues or bugs
- Maintenance: Every file addition or removal must be logged in the project's Changelog table immediately [790, conversation history].
2. Pattern Reference Integrity
- Rule: Consult the Pattern Document at the start of every session [790, conversation history].
- Purpose: Inherit previous design decisions and established engineering patterns to avoid "re-litigating" resolved questions and prevent "GIST debt" (uncertainty-driven technical debt) [790, 885, conversation history].
- Grounding: Every entry must reflect the actual codebase, never aspirational designs.
3. Automated Maintenance via Agentic Skills
- Rule: Utilize the scripts/ folder for project hygiene [790, conversation history].
- Action: When a file is expected but missing, or environment state is drift-prone, use Shell Mode to run maintenance scripts autonomously [768, conversation history].
- Local Delegation: Identify "tedious tasks" (e.g., regex, boilerplate) to be offloaded to the local Ollama instance to preserve Gemini API quota [14, 27, conversation history].
4. Continuous API Validation (Bruno)
- Rule: No backend API feature is complete until the Bruno pipeline is updated [790, conversation history].
- Documentation: Maintain an .md file in the Bruno folder that generates a visual HTML flow of the tests [790, conversation history].
- Gated Commits: Successful Bruno execution is required for all commits.
- Exceptions: Requires the exact string: "I understand bruno validation is failing and I allow the exception to have the code committed to github repo".
- Definition of Done: A feature is "done" only when it passes the automated validation and its visual flow is verified for correctness [790, conversation history].
5. Infrastructure-as-Code & Cost Gating
- Rule: Every infra-dependent feature requires a Terraform update (targeting AWS/Google Cloud) [790, conversation history].
- Infrastructure Gate: The agent must calculate projected costs and run a terraform plan before any GitHub tagging [790, conversation history].
- Deployment: Deployment triggers automatically upon GitHub tagging; tagging is prohibited until cost and infra reviews are finalized [790, conversation history].

--------------------------------------------------------------------------------
Operational Protocols
The 80/20 Surgical Strike Methodology
- Plan-First: Spend 80% of the session in Plan Mode (read-only analysis) and only 20% in execution
- Scope: Limit each session to one testable change to prevent "cascade damage" and minimize technical debt

Communication Guidelines
- Clarity: Always ask clarifying questions before acting on ambiguous prompts
- Accountability: If you cannot explain why a specific line of code is necessary, do not implement it
- Fresh Context: Start new conversations frequently to avoid "context rot" and performance degradation in long threads