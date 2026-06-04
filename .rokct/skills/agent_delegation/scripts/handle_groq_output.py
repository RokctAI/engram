# Licensed under the MIT License.
# Copyright 2024 RokctAI

import os
import sys
import re
import json
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from update_classifications import is_duplicate_theme

def set_field(content, field, value):
    if re.search(rf'^{field}:', content, re.MULTILINE):
        return re.sub(rf'^{field}:.*', f'{field}: {value}', content, flags=re.MULTILINE)
    else:
        if '---' in content:
            parts = content.rsplit('---', 1)
            return f"{parts[0]}{field}: {value}\n---{parts[1]}"
        return f"{content}\n{field}: {value}"

def handle_groq_output(level, content, file_path=None):
    """Parses Groq output and performs file operations based on the pipeline level."""
    print(f"🛠️ Processing Groq Output for Level {level}...")

    job_dir = Path('.rokct/agent/jobs/pending')
    job_dir.mkdir(parents=True, exist_ok=True)
    themes_path = Path('.rokct/config/classifications/factory_themes.txt')

    if level == 0:
        # Level 0: Expected output is a list of themes
        # Format: theme | type
        lines = content.strip().split('\n')
        count = 0
        for line in lines:
            if '|' not in line: continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 2: continue

            theme = parts[0]
            book_type = parts[1].lower()

            # Deduplication Check
            is_dup, matched = is_duplicate_theme(theme, str(themes_path))
            if is_dup:
                print(f"⏭️ Skipping duplicate theme: {theme} (similar to: {matched})")
                continue

            # Create a new job card
            hash_str = hashlib.sha256(f"{theme}{book_type}{datetime.now()}".encode()).hexdigest()[:6]
            filename = f"{theme.replace(' ', '_').lower()}_{book_type}_{hash_str}.md"

            card_content = f"""<!-- CARD RULES
     This card is the source of truth for this job.
     Status field controls pipeline progression.
     All status changes must go through update_status.py.
     Direct edits to status field will be rejected by the state machine.
-->
---
id: {theme.replace(' ', '_').lower()}_{hash_str}
theme: {theme}
type: {book_type}
age:
metarules:
guardrail:
idea:
idea_status:
concept:
concept_status:
rules_status:
book_name:
book_path:
status: theme_generated
created: {datetime.now().strftime('%Y-%m-%d')}
last_updated: {datetime.now().strftime('%Y-%m-%d')}
session_id:
session_started:
attempts: 0
last_error:
loop_iterations: 0
max_iterations: 10
---
"""
            with open(job_dir / filename, 'w') as f:
                f.write(card_content)
            print(f"✅ Created job card: {filename}")
            count += 1

        # Update classifications after creating new cards
        try:
            scripts_dir = Path(__file__).parent
            subprocess.run(['python', str(scripts_dir / 'update_classifications.py')], check=True)
        except Exception as e:
            print(f"⚠️ Failed to update classifications: {e}")

        return count > 0

    elif level == 1:
        # Level 1: Expected output is 5 ideas for a specific card
        if not file_path:
            print("Error: --file is required for Level 1 output handling.")
            return False

        card_path = Path(file_path)
        if not card_path.exists():
            print(f"Error: Card file {file_path} not found.")
            return False

        with open(card_path, 'r', encoding='utf-8') as f:
            card_content = f.read()

        # Clean up content (remove conversational filler if any)
        ideas = content.strip()

        # Update the card content
        updated_content = set_field(card_content, "idea", ideas.replace('\n', ' '))

        with open(card_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        # Use update_status.py to handle the state transition
        try:
            scripts_dir = Path(__file__).parent
            subprocess.run([
                'python', str(scripts_dir / 'update_status.py'),
                '--file', str(card_path),
                '--status', 'pending_approval',
                '--agent', 'groq'
            ], check=True)
            print(f"✅ Updated card {file_path} with ideas and status 'pending_approval'.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to update status for {file_path}: {e}")
            return False

    return False

def main():
    parser = argparse.ArgumentParser(description="Handle Groq output.")
    parser.add_argument("--level", type=int, required=True, help="Pipeline level (0-6)")
    parser.add_argument("--content", required=True, help="Content from Groq")
    parser.add_argument("--file", help="Path to the job card file (required for level > 0)")

    args = parser.parse_args()

    success = handle_groq_output(args.level, args.content, args.file)
    if not success:
        print("⚠️ No actionable content found in Groq output.")
        exit(1)

if __name__ == "__main__":
    main()
