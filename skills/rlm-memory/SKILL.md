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
- **Fixed Root**: `.opencode` ALWAYS stays at terminal launch directory

## Core Architecture

### Terminal Launch Directory (CRITICAL)

**ALWAYS use the directory where the terminal was launched as the root for `.opencode`**

The `.opencode` directory is NEVER created inside project subdirectories. It always stays at the terminal launch directory level.

**Examples:**

✓ **Correct:**
```
Terminal launched in: ~/workspace/
.opencode location:   ~/workspace/.opencode/

Working on:           ~/workspace/frontend/src/components/
.opencode location:   ~/workspace/.opencode/  (NOT ~/workspace/frontend/.opencode/)

Working on:           ~/workspace/booking-system/api/
.opencode location:   ~/workspace/.opencode/  (NOT ~/workspace/booking-system/.opencode/)
```

✗ **Incorrect:**
```
Terminal launched in: ~/workspace/
Working on:           ~/workspace/frontend/
.opencode location:   ~/workspace/frontend/.opencode/  ← WRONG!
```

**Implementation Strategy:**

At the start of ANY task, determine the root directory:

```bash
# Method 1: Use environment variable (if terminal sets it)
LAUNCH_DIR="${TERMINAL_LAUNCH_DIR:-$(pwd)}"

# Method 2: Look for existing .opencode upward
LAUNCH_DIR=$(pwd)
while [[ "$LAUNCH_DIR" != "/" ]]; do
  if [[ -d "$LAUNCH_DIR/.opencode" ]]; then
    break
  fi
  LAUNCH_DIR=$(dirname "$LAUNCH_DIR")
done

# If no .opencode found, use current directory
[[ "$LAUNCH_DIR" == "/" ]] && LAUNCH_DIR=$(pwd)

# Set the root
OPENCODE_ROOT="$LAUNCH_DIR/.opencode"
```

**Path Resolution Rules:**

1. **BEFORE any memory operation**, resolve the `.opencode` root
2. **Check upward** from current directory for existing `.opencode`
3. **If found**, use that directory as root
4. **If not found**, use the current directory
5. **NEVER create** `.opencode` inside subdirectories

### Single Global Memory File

Location: `$OPENCODE_ROOT/rlm_state/memory_store.pkl`

Contains:
- Task metadata (project ID, description, files, timestamps)
- Embeddings (Sentence Transformers)
- Serialized state

### Project Folder Structure

```
$OPENCODE_ROOT/rlm_state/projects/
  dashboard-redesign/
    0001-layout-analysis.md
    0002-modal-implementation.md
  invoice-system/
    0001-pdf-parser.md
  frontend-refactor/
    0001-component-analysis.md
  booking-system/
    0001-api-design.md
```

**Key Points:**
- Only `.md` files live in project folders
- No metadata, no embeddings in project folders
- Project names can match subdirectory names (e.g., "frontend", "booking-system")
- But the `.opencode` structure is ALWAYS at the root level

## Critical Rule: Embedding-First Resolution

**ALWAYS follow this order:**

1. **Resolve .opencode Root Directory**
   - Find existing `.opencode` by searching upward
   - Or use current directory if none exists
   - Set `OPENCODE_ROOT` variable

2. **Semantic Search First**
   - Query embeddings in global memory file
   - Check if related project exists

3. **Project Exists?**
   - Load previous memory
   - Read relevant `.md` files via RLM
   - Continue task numbering
   - Append to global memory

4. **Project Doesn't Exist?**
   - Create new project folder (under `$OPENCODE_ROOT/rlm_state/projects/`)
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

#### 0. Resolve .opencode Root (ALWAYS FIRST)

```bash
# Find the .opencode root directory
CURRENT_DIR=$(pwd)
LAUNCH_DIR="$CURRENT_DIR"

# Search upward for existing .opencode
while [[ "$LAUNCH_DIR" != "/" ]]; do
  if [[ -d "$LAUNCH_DIR/.opencode" ]]; then
    echo "Found .opencode at: $LAUNCH_DIR/.opencode"
    break
  fi
  LAUNCH_DIR=$(dirname "$LAUNCH_DIR")
done

# If not found, use current directory
if [[ "$LAUNCH_DIR" == "/" ]]; then
  LAUNCH_DIR="$CURRENT_DIR"
  echo "No .opencode found. Will create at: $LAUNCH_DIR/.opencode"
fi

OPENCODE_ROOT="$LAUNCH_DIR/.opencode"
export OPENCODE_ROOT

# ALL subsequent commands use $OPENCODE_ROOT
```

#### 1. Initialize Memory System

```bash
# First time only - creates global memory file at $OPENCODE_ROOT
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py init --root "$OPENCODE_ROOT"

# Check status
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py status --root "$OPENCODE_ROOT"
```

#### 2. Resolve Project (Embedding-First)

```bash
# Search for existing related projects
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
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

**Refer to**: `$OPENCODE_ROOT/skills/rlm/SKILL.md`

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
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py add-task \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign" \
  --description "Analyzed modal component layout and interactions" \
  --files-read "src/components/Modal.tsx,src/utils/helpers.ts" \
  --output-file "$OPENCODE_ROOT/rlm_state/projects/dashboard-redesign/0003-modal-analysis.md"

# This automatically:
# - Generates embedding for the task
# - Assigns next task number
# - Updates global memory file at $OPENCODE_ROOT
```

#### 6. Create Output Markdown

Write the task output to the numbered `.md` file:

```bash
cat > $OPENCODE_ROOT/rlm_state/projects/dashboard-redesign/0003-modal-analysis.md <<'EOF'
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
# Always resolve root first
OPENCODE_ROOT=$(resolve_opencode_root)

python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py status --root "$OPENCODE_ROOT"
# Shows:
# - Total projects: 5
# - Total tasks: 23
# - Last active project: dashboard-redesign
```

**During Session:**
```bash
# Find related past work
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
  --query "modal component validation"

# Review specific project history
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py project-history \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign"
```

**On Session End:**
Memory automatically persists. No manual save needed.

## Memory REPL Commands

**ALL commands now require `--root` parameter to specify the .opencode location.**

### init
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py init --root "$OPENCODE_ROOT"
```
Creates global memory file at the specified root. Run once per workspace.

### status
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py status --root "$OPENCODE_ROOT"
```
Shows total projects, tasks, and last activity.

### search
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
  --query "user authentication flow" \
  --top-k 5
```
Semantic search across all tasks. Returns matching projects and tasks.

### add-task
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py add-task \
  --root "$OPENCODE_ROOT" \
  --project "invoice-system" \
  --description "Implemented PDF parsing for invoices" \
  --files-read "invoices/sample.pdf,src/parser.py" \
  --output-file "$OPENCODE_ROOT/rlm_state/projects/invoice-system/0001-pdf-parser.md"
```
Records new task with automatic embedding and numbering.

### project-history
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py project-history \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign"
```
Lists all tasks for a specific project in chronological order.

### create-project
```bash
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py create-project \
  --root "$OPENCODE_ROOT" \
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
# 0. Resolve .opencode root
OPENCODE_ROOT=$(resolve_opencode_root)

# 1. Search for related project
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
  --query "analyze TypeScript components"

# 2. Found existing project: "component-refactor"

# 3. Read new file via RLM
python3 $OPENCODE_ROOT/skills/rlm/scripts/rlm_repl.py init src/NewComponent.tsx
python3 $OPENCODE_ROOT/skills/rlm/scripts/rlm_repl.py exec -c "print(peek(0, 5000))"

# 4. Do the analysis work
# [Perform analysis...]

# 5. Record in memory
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py add-task \
  --root "$OPENCODE_ROOT" \
  --project "component-refactor" \
  --description "Analyzed NewComponent.tsx for refactoring opportunities" \
  --files-read "src/NewComponent.tsx" \
  --output-file "$OPENCODE_ROOT/rlm_state/projects/component-refactor/0004-new-component.md"

# 6. Write the output markdown
cat > $OPENCODE_ROOT/rlm_state/projects/component-refactor/0004-new-component.md <<'EOF'
# NewComponent.tsx Analysis
...
EOF
```

## Guardrails

- **Fixed .opencode location**: ALWAYS at terminal launch directory, NEVER in project subdirectories
- **Resolve root first**: Before ANY memory operation, determine `OPENCODE_ROOT`
- **Never duplicate projects**: Always search embeddings first
- **No metadata in project folders**: Only `.md` files
- **Single source of truth**: Global memory file only
- **RLM for reading**: Never reimplement file inspection
- **Keep state under**: `$OPENCODE_ROOT/rlm_state/`
- **No subagents**: Memory-RLM is root-level only
- **Automatic numbering**: Task numbers assigned sequentially per project

## Example: Multi-Session Project with Directory Navigation

**Terminal launched in:** `~/workspace/`

**Session 1 (working in ~/workspace/frontend/):**
```bash
cd ~/workspace/frontend/

# Resolve root (finds ~/workspace/.opencode or creates it)
OPENCODE_ROOT=~/workspace/.opencode

# User: "Analyze the dashboard layout"
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
  --query "dashboard"
# Result: No match. Create new project.

python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py create-project \
  --root "$OPENCODE_ROOT" \
  --name "dashboard-redesign"

# RLM analysis of frontend/src/dashboard/...
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py add-task \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign" \
  --description "Initial dashboard layout analysis" \
  --output-file "$OPENCODE_ROOT/rlm_state/projects/dashboard-redesign/0001-layout-analysis.md"

# .opencode stays at ~/workspace/.opencode ✓
```

**Session 2 (working in ~/workspace/booking-system/):**
```bash
cd ~/workspace/booking-system/

# Resolve root (finds existing ~/workspace/.opencode)
OPENCODE_ROOT=~/workspace/.opencode

# User: "Add modal component to the dashboard"
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py search \
  --root "$OPENCODE_ROOT" \
  --query "dashboard modal"
# Result: Found "dashboard-redesign" (similarity: 0.85)

python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py project-history \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign"
# Shows task 0001. Next task will be 0002.

# RLM analysis of modal code in booking-system/...
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py add-task \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign" \
  --description "Modal component integration analysis" \
  --output-file "$OPENCODE_ROOT/rlm_state/projects/dashboard-redesign/0002-modal-integration.md"

# Still using ~/workspace/.opencode ✓
# NOT creating ~/workspace/booking-system/.opencode ✓
```

**Session 3 (working in ~/workspace/api/):**
```bash
cd ~/workspace/api/

# Resolve root (finds existing ~/workspace/.opencode)
OPENCODE_ROOT=~/workspace/.opencode

# User: "Review what we did with the dashboard"
python3 $OPENCODE_ROOT/skills/rlm-memory/scripts/memory_repl.py project-history \
  --root "$OPENCODE_ROOT" \
  --project "dashboard-redesign"
# Shows:
# 0001-layout-analysis.md
# 0002-modal-integration.md

# Read via RLM
python3 $OPENCODE_ROOT/skills/rlm/scripts/rlm_repl.py init \
  $OPENCODE_ROOT/rlm_state/projects/dashboard-redesign/0001-layout-analysis.md
python3 $OPENCODE_ROOT/skills/rlm/scripts/rlm_repl.py exec -c "print(content)"

# All memory still in ~/workspace/.opencode ✓
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

**Correct structure (example: terminal launched in ~/workspace/):**

```
~/workspace/
  .opencode/                           # ← ROOT LEVEL ONLY
    rlm_state/
      memory_store.pkl                 # Single global memory file
      projects/                        # All project folders
        dashboard-redesign/
          0001-layout-analysis.md
          0002-modal-integration.md
        booking-system/
          0001-api-design.md
        frontend-refactor/
          0001-component-analysis.md
      state.pkl                        # RLM state (separate)
      chunks/                          # RLM chunks (separate)
    skills/
      rlm/
        scripts/
          rlm_repl.py                  # Original RLM
      rlm-memory/
        scripts/
          memory_repl.py               # Memory extension
  
  frontend/                            # ← NO .opencode here
    src/
      components/
      dashboard/
  
  booking-system/                      # ← NO .opencode here
    api/
    models/
  
  api/                                 # ← NO .opencode here
    routes/
    controllers/
```

## Troubleshooting

**Problem**: `.opencode` created in subdirectory (e.g., `~/workspace/frontend/.opencode/`)
**Solution**: You didn't resolve the root first. Always search upward for existing `.opencode` before any operation.

**Problem**: Multiple `.opencode` directories in different subdirectories
**Solution**: Delete the subdirectory ones. Keep only the root-level `.opencode`. Update scripts to search upward.

**Problem**: Duplicate projects created
**Solution**: You skipped embedding search. Always run `search` first.

**Problem**: Can't find past tasks
**Solution**: Use `search` with semantic query, not exact project name.

**Problem**: Task numbering reset
**Solution**: Check `project-history` to see current max task number.

**Problem**: Memory file corrupted
**Solution**: Backup at `$OPENCODE_ROOT/rlm_state/memory_store.pkl.backup` auto-created on each write.

**Problem**: Working in subdirectory but can't find `.opencode`
**Solution**: Scripts should search upward. Manually set `OPENCODE_ROOT` environment variable if needed.

## Summary

Memory-RLM = RLM + Memory + Embeddings + Fixed Root

- **Fixed Root**: `.opencode` ALWAYS at terminal launch directory
- **RLM**: Reads any file type, chunks, searches
- **Memory**: Single global file, tracks all projects/tasks
- **Embeddings**: Semantic search prevents duplicates
- **Output**: Numbered `.md` files per project
- **Sessions**: Full continuity across time

Always: **Resolve Root** → Search → Resolve → Read (RLM) → Work → Record → Output

**Key Rule**: Before ANY memory operation, resolve `OPENCODE_ROOT` by searching upward for existing `.opencode` directory.