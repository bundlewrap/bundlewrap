# AI Usage Policy

## Philosophy: AI-Augmented Engineering vs. AI-Generated Code

We distinguish between two fundamentally different approaches to AI:

1. *AI-Generated Code (Problematic):* Handing off a problem to an AI and copy-pasting the output. This leads to "plausible" but buggy code, increased review fatigue, and a loss of deep system knowledge.

2. *AI-Augmented Engineering (Allowed):* Using AI as an assistant to accelerate an engineer's existing plan. The human remains the architect; the AI is the high-speed drafter.

If a contributor chooses to use AI, our goal is to foster *AI-Augmented Engineering*. We value the "handcrafted" quality of BundleWrap and want AI to reduce friction, not to bypass thinking.

## Core Principles

### Absolute Accountability
The human contributor is 100% responsible for every character in a Pull Request. If you cannot explain the *why* behind every line, do not commit it.

### Conceptual Independence
Design the logic and architecture of a feature *before* engaging with AI. AI should not be used to solve "what should we do?" but rather "how do I write this specific Python implementation of our decided plan?".

### Reviewability & Pruning
AI output is often verbose. You are required to manually prune and refine AI output to its most concise and idiomatic form before submission. Small, focused PRs are mandatory.

### Legal & Licensing Integrity
- *No License Laundering:* Do not use AI to generate large, unique logic blocks that might have been trained on incompatible licenses.
- *Human Authorship:* To ensure BundleWrap remains protectable under its license, significant human creative direction is required.
- *Dependency Guardrails:* Verify all third-party library suggestions for license compatibility and security.

### Preservation of "Design Pressure"
"Monkey work" (writing docs or tests) is a valuable feedback loop. If writing tests for your code feels too difficult even with AI assistance, your code design is likely too complex. Use this "pain" as a signal to refactor.

## Tool Configuration
All contributors using AI tools must point their tools to the `.ai-instructions.md` file in the repository root. If your tool needs its own specific path, create a symlink and add it to your *local* gitignore.
