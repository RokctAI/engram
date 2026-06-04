---
name: StartupOS Compiler & Conversational Bridge
description: Local project wrappers that interface with the canonical ROKCT Protocol StartupOS core engine to compile corporate and life strategic canvases, provision new startup directories, and log real-time conversational achievements.
---

# StartupOS Local Project Capability Specification

This directory houses the local project **callers and wrappers** for the **StartupOS Compiler Engine**. It maps local workspace inputs (like `instances/`) to the canonical ROKCT Protocol codebase stored under `The-Rokct-Protocol/core/skills/startup_os/`.

## Local Workspace Directory Layout

```text
factory/.rokct/skills/startup_os/
├── SKILL.md                         # This file (local capability specs)
└── scripts/
    ├── compile.py                   # Wrapper calling core/compiler.py compile_instance
    ├── provision.py                 # Wrapper calling core/agent_bridge.py auto_provision_profile
    └── log_milestone.py             # Wrapper calling core/agent_bridge.py log_ambient_milestone
```

## How to Use (factory)

### 1. Compile Strategic Profile
To compile a specific local business or life strategic profile into its downstream markdown canvases and plans:
```bash
python .rokct/skills/startup_os/scripts/compile.py --type business --name SouthRiver
python .rokct/skills/startup_os/scripts/compile.py --type life --name Rendani
```

### 2. Auto-Provision New Profile
When a user signs up, the gateway can invoke this local wrapper to create their new strategic questions directory:
```bash
python .rokct/skills/startup_os/scripts/provision.py --type business --name TableMountainTech --base "Cape Town, South Africa"
```

### 3. Log Conversational Milestone
When the user shares achievements verbally over WhatsApp, Next.js, or other channels, Hermes logs the milestone into their Single Source of Truth file:
```bash
python .rokct/skills/startup_os/scripts/log_milestone.py --name Rendani --category "Technical Mastery" --entry "Engineered ROKCT Protocol modular skills architecture wrappers"
```
