---
name: rlm-memory
description: Extended RLM with persistent global memory and semantic search. Tracks AI actions across projects, prevents folder duplication, and maintains continuity across sessions.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
---

# rlm-memory (Memory-Enhanced Recursive Language Model)

Use this Skill when:
- You need RLM's file-reading capabilities PLUS persistent memory across sessions
- Working on multi-session projects where continuity matters
- The user wants AI actions tracked and searchable
- Preventing duplicate project folders is important

## Mental Model

- **RLM Layer**: Reads files of any type (ts, tsx, js, pdf, txt, etc.) via `rlm_repl.py`
- **Memory Layer**: Single global memory file stores all project metadata + embeddings
- **Embedding-First**: Always search before creating new projects
- **Project Folders**: Contain ONLY `.md` outputs, numbered sequentially

## Core Architecture

### Single Global Memory File

Location: `.opencode/rlm_state/memory_store.pkl`

Contains:
- Task metadata (project ID, description, files, timestamps)
- Embeddings (Sentence Transformers)
- Serialized state

### Project Folder Structure

```
.opencode/rlm_state/projects/
  dashboard-redesign/
    0001-layout-analysis.md
    0002-modal-implementation.md
  invoice-system/
    0001-pdf-parser.md
```

Only `.md` files live in project folders. No metadata, no embeddings.

## Critical Rule: Embedding-First Resolution

**ALWAYS follow this order:**

1. **Semantic Search First**
   - Query embeddings in global memory file
   - Check if related project exists

2. **Project Exists?**
   - Load previous memory
   - Read relevant `.md` files via RLM
   - Continue task numbering
   - Append to global memory

3. **Project Doesn't Exist?**
   - Create new project folder
   - Initialize in global memory
   - Start from task 0001

This guarantees NO duplicate folders.

## Workflow

### Inputs

Accept from `$ARGUMENTS`:
- `query=<task description>` (required): What the user wants
- `context=<path>` (optional): File to read via RLM
- `project=<name>` (optional): Force specific project name

If missing, ask the user for:
1. Task description
2. Any context files to analyze

### Step-by-Step Procedure

#### 1. Initialize Memory System

```bash
# First time only - creates global memory file
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py init

# Check status
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py status
```

#### 2. Resolve Project (Embedding-First)

```bash
# Search for existing related projects
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search \
  --query "dashboard redesign layout" \
  --top-k 5

# Returns:
# - Matching projects with similarity scores
# - Last task number for each project
```

**Decision Point:**
- If similarity > 0.35: Use existing project
- If similarity < 0.35: Create new project

#### 3. Read Context via RLM (if needed)

If user provided context files, delegate to the RLM skill for file reading and analysis:

**Refer to**: `.opencode/skills/rlm/SKILL.md`

The RLM skill handles:
- Initializing and chunking any file type (ts, tsx, js, pdf, txt, etc.)
- Content scouting and inspection
- Pattern-based searching (grep)
- Relevant section extraction

Pass the context file path to the RLM skill and receive back:
- File content overview
- Relevant code/text sections
- Structural information (functions, classes, exports, etc.)

Once RLM completes its analysis, continue with task execution using the extracted information.

#### 4. Execute Task

Perform the actual work (analysis, code generation, etc.)

#### 5. Record Memory

```bash
# Add task to memory with embedding
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py add-task \
  --project "dashboard-redesign" \
  --description "Analyzed modal component layout and interactions" \
  --files-read "src/components/Modal.tsx,src/utils/helpers.ts" \
  --output-file ".opencode/rlm_state/projects/dashboard-redesign/0003-modal-analysis.md"

# This automatically:
# - Generates embedding for the task
# - Assigns next task number
# - Updates global memory file
```

#### 6. Create Output Markdown

Write the task output to the numbered `.md` file:

```bash
cat > .opencode/rlm_state/projects/dashboard-redesign/0003-modal-analysis.md <<'EOF'
# Modal Component Analysis

## Files Analyzed
- src/components/Modal.tsx
- src/utils/helpers.ts

## Findings
[Your analysis here]

## Recommendations
[Your recommendations here]
EOF
```

### Session Continuity

**On Session Start:**
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py status
# Shows:
# - Total projects: 5
# - Total tasks: 23
# - Last active project: dashboard-redesign
```

**During Session:**
```bash
# Find related past work
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search \
  --query "modal component validation"

# Review specific project history
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py project-history \
  --project "dashboard-redesign"
```

**On Session End:**
Memory automatically persists. No manual save needed.

## Memory REPL Commands

### init
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py init
```
Creates global memory file. Run once per machine.

### status
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py status
```
Shows total projects, tasks, and last activity.

### search
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search \
  --query "user authentication flow" \
  --top-k 5
```
Semantic search across all tasks. Returns matching projects and tasks.

### add-task
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py add-task \
  --project "invoice-system" \
  --description "Implemented PDF parsing for invoices" \
  --files-read "invoices/sample.pdf,src/parser.py" \
  --output-file ".opencode/rlm_state/projects/invoice-system/0001-pdf-parser.md"
```
Records new task with automatic embedding and numbering.

### project-history
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py project-history \
  --project "dashboard-redesign"
```
Lists all tasks for a specific project in chronological order.

### create-project
```bash
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py create-project \
  --name "new-feature-analysis"
```
Manually creates a new project folder and initializes it in memory.

## Integration with RLM

Memory-RLM **wraps** RLM, never replaces it.

**For file reading:**
- Always use `rlm_repl.py` for context inspection
- Supports all file types: `.ts`, `.tsx`, `.js`, `.pdf`, `.txt`, etc.
- Use RLM's chunking for large files

**For memory:**
- Use `memory_repl.py` for project/task tracking
- Single global memory file
- Embedding-first search

**Example combined workflow:**

```bash
# 1. Search for related project
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search \
  --query "analyze TypeScript components"

# 2. Found existing project: "component-refactor"
# 3. Read new file via RLM
python3 .opencode/skills/rlm/scripts/rlm_repl.py init src/NewComponent.tsx
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(peek(0, 5000))"

# 4. Do the analysis work
# [Perform analysis...]

# 5. Record in memory
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py add-task \
  --project "component-refactor" \
  --description "Analyzed NewComponent.tsx for refactoring opportunities" \
  --files-read "src/NewComponent.tsx" \
  --output-file ".opencode/rlm_state/projects/component-refactor/0004-new-component.md"

# 6. Write the output markdown
# [Write analysis to the .md file...]
```

## Guardrails

- **Never duplicate projects**: Always search embeddings first
- **No metadata in project folders**: Only `.md` files
- **Single source of truth**: Global memory file only
- **RLM for reading**: Never reimplement file inspection
- **Keep state under**: `.opencode/rlm_state/`
- **No subagents**: Memory-RLM is root-level only
- **Automatic numbering**: Task numbers assigned sequentially per project

## Example: Multi-Session Project

**Session 1:**
```bash
# User: "Analyze the dashboard layout"
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search --query "dashboard"
# Result: No match. Create new project.

python3 .opencode/skills/rlm-memory/scripts/memory_repl.py create-project --name "dashboard-redesign"
# RLM analysis...
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py add-task \
  --project "dashboard-redesign" \
  --description "Initial dashboard layout analysis" \
  --output-file ".opencode/rlm_state/projects/dashboard-redesign/0001-layout-analysis.md"
```

**Session 2 (days later):**
```bash
# User: "Add modal component to the dashboard"
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py search --query "dashboard modal"
# Result: Found "dashboard-redesign" (similarity: 0.85)

python3 .opencode/skills/rlm-memory/scripts/memory_repl.py project-history --project "dashboard-redesign"
# Shows task 0001. Next task will be 0002.

# RLM analysis of modal code...
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py add-task \
  --project "dashboard-redesign" \
  --description "Modal component integration analysis" \
  --output-file ".opencode/rlm_state/projects/dashboard-redesign/0002-modal-integration.md"
```

**Session 3 (weeks later):**
```bash
# User: "Review what we did with the dashboard"
python3 .opencode/skills/rlm-memory/scripts/memory_repl.py project-history --project "dashboard-redesign"
# Shows:
# 0001-layout-analysis.md
# 0002-modal-integration.md

# Read via RLM
python3 .opencode/skills/rlm/scripts/rlm_repl.py init .opencode/rlm_state/projects/dashboard-redesign/0001-layout-analysis.md
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(content)"
```

## When to Use Memory-RLM vs Plain RLM

**Use Memory-RLM when:**
- Multi-session projects
- Need to track AI actions
- Want semantic search across past work
- Continuity matters
- Multiple related tasks over time

**Use Plain RLM when:**
- One-off file analysis
- Single session work
- No need for memory
- Simple chunk-and-extract tasks

## File Locations

```
.opencode/
  rlm_state/
    memory_store.pkl          # Single global memory file
    projects/                 # All project folders
      project-name-1/
        0001-task.md
        0002-task.md
      project-name-2/
        0001-task.md
    state.pkl                 # RLM state (separate)
    chunks/                   # RLM chunks (separate)
  skills/
    rlm/
      scripts/
        rlm_repl.py           # Original RLM
    rlm-memory/
      scripts/
        memory_repl.py        # Memory extension
```

## Troubleshooting

**Problem**: Duplicate projects created
**Solution**: You skipped embedding search. Always run `search` first.

**Problem**: Can't find past tasks
**Solution**: Use `search` with semantic query, not exact project name.

**Problem**: Task numbering reset
**Solution**: Check `project-history` to see current max task number.

**Problem**: Memory file corrupted
**Solution**: Backup at `.opencode/rlm_state/memory_store.pkl.backup` auto-created on each write.

## Summary

Memory-RLM = RLM + Memory + Embeddings

- **RLM**: Reads any file type, chunks, searches
- **Memory**: Single global file, tracks all projects/tasks
- **Embeddings**: Semantic search prevents duplicates
- **Output**: Numbered `.md` files per project
- **Sessions**: Full continuity across time

Always: Search → Resolve → Read (RLM) → Work → Record → Output