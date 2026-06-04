# Agent Delegation Skills (Factory Context)

This directory contains essential automation skills adapted from the opportunities registry to serve the autonomous factory.

## Core Skills

### 1. Agent Delegation (`delegate_to_agent.py`)
CLI tool for creating and managing AI agent sessions. It is the primary interface for triggering complex tasks across all pipeline levels.

### 2. Link Health Check (`check_health.py`)
Scans job cards and book drafts for broken links, ensuring that reference materials and published assets remain accessible.

### 3. PII Privacy Sync (`privacy_sync.py` & `crypto_utils.py`)
Enforces encryption for any personally identifiable information (PII) found in job cards, protecting contributor and user data.

### 4. Audit Log Management (`update_audit_logs.py`)
Maintains `job_audit_log.md` files in draft and published directories, providing automated tracking of book progress.

### 5. Classification Updates (`update_classifications.py`)
Generates reference files for all themes and genres in the pipeline, used by agents for consistency and duplication checks.

### 6. Factory Dashboard (`update_dashboard.py`)
Recalculates real-time factory statistics and updates the main README.md dashboard with the current system state.

### 7. Production Kits (`response_kits.py`)
Scaffolds new book directories in `books/drafts/` when a concept is approved, ensuring a standardized project structure from the start.
