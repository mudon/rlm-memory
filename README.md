# rlm-memory OpenCode Integration

A guide for installing and integrating rlm-memory into OpenCode using a centralized management structure with symlinks.

## Overview

This integration approach provides:

- ✅ **One global install** – Single source of truth for all managed skills
- ✅ **No duplicated files** – Symlinks keep everything synchronized
- ✅ **Multi-project sharing** – Same skills and agents across all projects
- ✅ **Easy updates & rollback** – Update once, apply everywhere

## Prerequisites

Before starting, ensure you have:

- Git installed
- OpenCode installed and configured
- Unix-like system (Linux or macOS)
- Shell with symlink support (bash, zsh, etc.)

## Directory Philosophy

This setup uses three key locations:

- `~/.config/opencode/rlm-management` → Single source of truth for managed skills
- `~/.config/opencode/skills` → Global skills that OpenCode loads (symlinks)
- `<project>/.opencode` → Project-local view (symlinks, no copies)

## Installation

### Step 1: Clone rlm-memory

```bash
git clone https://github.com/mudon/rlm-memory.git
```

### Step 2: Create Management Directory

```bash
mkdir -p ~/.config/opencode/rlm-management/.opencode/
```

Move the cloned repository into the management structure:

```bash
mv rlm-memory ~/.config/opencode/rlm-management/.opencode/
```

### Step 3: Expose Skills Globally

Create symlinks so OpenCode can discover the skills:

**rlm-memory skill:**
```bash
ln -s \
  ~/.config/opencode/rlm-management/.opencode/skills/rlm-memory \
  ~/.config/opencode/skills/rlm-memory
```

**rlm core skill:**
```bash
ln -s \
  ~/.config/opencode/rlm-management/.opencode/skills/rlm \
  ~/.config/opencode/skills/rlm
```

At this point, OpenCode can load both skills globally.

### Step 4: Project Setup

Navigate to your project and create the required structure:

```bash
cd <project-directory>
mkdir -p .opencode/skills/rlm-memory/scripts
```

### Step 5: Link rlm-memory Script

Symlink the memory REPL script into your project:

```bash
ln -s \
  ~/.config/opencode/rlm-management/.opencode/skills/rlm-memory/scripts/memory_repl.py \
  <project-directory>/.opencode/skills/rlm-memory/scripts/memory_repl.py
```

### Step 6: Link Global Agents (Optional)

If your project should use globally defined OpenCode agents:

```bash
mv 
  ~/.config/opencode/rlm-management/.opencode/agents
  ~/.config/opencode/rlm-management/agents
```

```bash
ln -s \
  ~/.config/opencode/rlm-management/agents \
  <project-directory>/.opencode/agents
```

## Final Directory Layout

### Global OpenCode Configuration

```
~/.config/opencode/
├── agents/
├── skills/
│   ├── rlm -> ~/.config/opencode/rlm-management/.opencode/skills/rlm
│   └── rlm-memory -> ~/.config/opencode/rlm-management/.opencode/skills/rlm-memory
└── rlm-management/
    └── .opencode/
        └── skills/
            ├── rlm/
            └── rlm-memory/
```

### Project Structure

```
<project-directory>/
└── .opencode/
    ├── agents -> ~/.config/opencode/agents
    └── skills/
        └── rlm-memory/
            └── scripts/
                └── memory_repl.py -> (symlink to global)
```

## Updating

To update rlm-memory across all projects:

```bash
cd ~/.config/opencode/rlm-management/.opencode/skills/rlm-memory
git pull
```

All projects using the symlinked skills will automatically receive the update.

## Troubleshooting

### Skill not visible in OpenCode

Check that global symlinks exist:
```bash
ls -la ~/.config/opencode/skills
```

### Broken symlink

Recreate the symlink using the force flag:
```bash
ln -sf <source> <target>
```

### Permission issues

Ensure OpenCode has read permissions:
```bash
chmod -R u+r ~/.config/opencode/rlm-management
```

### Wrong config directory

Verify OpenCode is reading from the correct location. Check your OpenCode settings or environment variables.

## Uninstall / Cleanup

### Remove global symlinks (safe)

```bash
rm ~/.config/opencode/skills/rlm-memory
rm ~/.config/opencode/skills/rlm
```

### Remove project links

```bash
rm <project-directory>/.opencode/agents
rm -rf <project-directory>/.opencode/skills/rlm-memory
```

### Delete management directory (destructive)

⚠️ **Warning:** This removes the source repository.

```bash
rm -rf ~/.config/opencode/rlm-management
```

## Benefits of This Approach

1. **Centralized Management** – Update once, apply everywhere
2. **Version Control** – Easy rollback via git
3. **No Duplication** – Saves disk space and prevents version drift
4. **Project Isolation** – Projects can selectively include skills
5. **Clean Separation** – Management, global, and project layers are distinct

## License

See the [rlm-memory repository](https://github.com/mudon/rlm-memory) for licensing details.

## Contributing

For issues or improvements to rlm-memory itself, please visit the [GitHub repository](https://github.com/mudon/rlm-memory).

---

**Questions?** Check the troubleshooting section or open an issue in the rlm-memory repository.
