# rlm-memory OpenCode Integration

This guide explains how to install and link `rlm-memory` into OpenCode using the `.opencode` skill structure.

## Overview

* Clone `rlm-memory` once into your global OpenCode config
* Create the required `.opencode` directories
* Symlink the `memory_repl.py` script into any project that should use it

This keeps a single source of truth while allowing per-project usage.

## Prerequisites

* Git installed
* OpenCode installed and configured
* Unix-like environment (Linux / macOS)

## Global Installation (One-Time Setup)

### 1. Clone the repository

```bash
git clone https://github.com/mudon/rlm-memory.git
```

### 2. Create the OpenCode management directories

```bash
mkdir -p ~/.config/opencode/rlm-management/.opencode
```

### 3. Move the cloned repository

Move or place the cloned repository under the management directory so it ends up like this:

```
~/.config/opencode/rlm-management/.opencode/skills/rlm-memory/
```

You can accomplish this with:

```bash
mkdir -p ~/.config/opencode/rlm-management/.opencode/skills/
mv rlm-memory ~/.config/opencode/rlm-management/.opencode/skills/
```

*(Adjust if you already have a preferred layout.)*

## Project Setup (Per Project)

### 1. Create the required `.opencode` structure

Inside your project directory, create the required `.opencode` structure:

```bash
mkdir -p <your-project-directory>/.opencode/skills/rlm-memory/scripts
```

### 2. Link the Memory Script

Symlink the `memory_repl.py` script into your project:

```bash
ln -s \
  ~/.config/opencode/rlm-management/.opencode/skills/rlm-memory/scripts/memory_repl.py \
  <your-project-directory>/.opencode/skills/rlm-memory/scripts/memory_repl.py
```

This allows the project to use `rlm-memory` without duplicating files.

## Resulting Structure

Your project should now include:

```
<your-project-directory>/
└── .opencode/
    └── skills/
        └── rlm-memory/
            └── scripts/
                └── memory_repl.py -> (symlink)
```

## Verification

To verify the symlink was created correctly:

```bash
ls -la <your-project-directory>/.opencode/skills/rlm-memory/scripts/
```

You should see `memory_repl.py` pointing to the global installation path.

## Usage

Once set up, OpenCode will automatically detect and use the `rlm-memory` skill in your project. Refer to the [rlm-memory documentation](https://github.com/mudon/rlm-memory) for usage instructions.

## Notes

* Updating `rlm-memory` in the global directory automatically updates all linked projects
* If the symlink breaks, verify paths and permissions
* Use `ln -sf` to overwrite an existing link if needed
* On Windows, use `mklink` instead of `ln -s` (requires administrator privileges)

## Troubleshooting

### Symlink not working

If the symlink isn't working, check:

1. The source file exists at the global location
2. You have read permissions for the source file
3. The target directory exists

### Permission issues

Ensure you have write permissions in both:
- `~/.config/opencode/rlm-management/`
- `<your-project-directory>/.opencode/`

## License

See the [rlm-memory repository](https://github.com/mudon/rlm-memory) for licensing details.

## Contributing

For issues or improvements related to:
- **rlm-memory core functionality**: Submit issues to the [rlm-memory repository](https://github.com/mudon/rlm-memory)
- **This integration guide**: Feel free to submit pull requests or open issues

---

**Last Updated**: February 2026
