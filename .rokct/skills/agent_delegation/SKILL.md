---
name: Agent Delegation
description: Automates the offloading of repetitive or large-scale coding tasks to an AI agent (Jules) or direct Groq API calls.
---

This project's agent delegation layout extends The-Rokct-Protocol canonical (`core/skills/agent_delegation/scripts/SKILL.md`). Read that for: Architecture, Architecture diagram, Prerequisites, API Key Resolution, Subcommand reference, `init_protocol` procedure, Decision Framework, Best Practices.

## factory Project Layout

Wrappers live in `.rokct/skills/agent_delegation/scripts/` (copied from `The-Rokct-Protocol/core/skills/agent_delegation/scripts/utils/`, `delegate_to_agent.py` excluded). Redirect to `The-Rokct-Protocol/core/skills/agent_delegation/scripts/delegate_to_agent.py`.

| Script | Path |
|---|---|
| Jules wrapper | `.rokct/skills/agent_delegation/scripts/call_jules.py` |
| Groq wrapper | `.rokct/skills/agent_delegation/scripts/call_groq.py` |
| Groq output handler | `.rokct/skills/agent_delegation/scripts/handle_groq_output.py` |
| Session scheduler | `.rokct/skills/agent_delegation/scripts/manage_sessions.py` |
| Deduplication | `.rokct/skills/agent_delegation/scripts/update_classifications.py` |

## How to Use (factory)

### 1. Delegate to Jules

```bash
python .rokct/skills/agent_delegation/scripts/call_jules.py create \
  --repo "sources/github/RokctAI/factory" \
  --prompt "Your detailed task description here" \
  --title "Feature/Task Name"
```

Monitor status:

```bash
python .rokct/skills/agent_delegation/scripts/call_jules.py status --id "SESSION_ID"
```

### 2. Call Groq Directly

```bash
python .rokct/skills/agent_delegation/scripts/call_groq.py groq \
  --prompt "Your prompt here" \
  --system "Optional system prompt" \
  --model "llama-3.3-70b-versatile"
```

### 3. Handle Groq Output (Pipeline)

```bash
python .rokct/skills/agent_delegation/scripts/handle_groq_output.py \
  --level 0 \
  --content "$GROQ_RESPONSE"
```

Pipeline levels:
- **Level 0** — parses `theme | type` lines → creates `.rokct/agent/jobs/pending/` job cards.
- **Level 1** — parses 5 ideas per card (extension point).

### 4. Manage Sessions

```bash
python .rokct/skills/agent_delegation/scripts/manage_sessions.py
```

### 5. Approve Plans (Optional)

```bash
python .rokct/skills/agent_delegation/scripts/call_jules.py approve --id "SESSION_ID"
```
