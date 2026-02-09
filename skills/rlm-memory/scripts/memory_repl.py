#!/usr/bin/env python3
"""Persistent memory system for RLM-style workflows with semantic search using FAISS.

This script provides global memory across all projects:
- Single memory file (metadata + embeddings + state)
- FAISS for fast semantic search
- Automatic project resolution (no duplicates)
- Integration with RLM for file reading
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import textwrap
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print(
        "ERROR: sentence-transformers not installed. Run: pip install sentence-transformers --break-system-packages",
        file=sys.stderr,
    )
    sys.exit(1)

# FAISS for fast similarity search
try:
    import faiss
except ImportError:
    print("ERROR: faiss not installed. Run: pip install faiss-cpu", file=sys.stderr)
    sys.exit(1)


# -----------------------------
# Defaults
# -----------------------------
DEFAULT_MEMORY_PATH = Path(".opencode/rlm_state/memory_store.pkl")
DEFAULT_PROJECTS_ROOT = Path(".opencode/rlm_state/projects")
DEFAULT_MODEL = "all-mpnet-base-v2"


# -----------------------------
# Exceptions
# -----------------------------
class MemoryError(RuntimeError):
    pass


# -----------------------------
# Data Classes
# -----------------------------
@dataclass
class TaskData:
    task_id: str
    project: str
    task_num: int
    description: str
    files_read: List[str]
    files_created: List[str]
    output_file: Optional[str]
    timestamp: float
    embedding_idx: Optional[int] = None


@dataclass
class ProjectData:
    name: str
    created_at: float
    last_updated: float
    task_count: int
    folder_path: str


@dataclass
class MemoryStore:
    version: int = 2
    projects: Dict[str, ProjectData] = field(default_factory=dict)
    tasks: List[TaskData] = field(default_factory=list)
    embeddings: Optional[np.ndarray] = None  # Shape: (num_tasks, embedding_dim)
    embedding_metadata: List[Dict[str, Any]] = field(default_factory=list)
    faiss_index: Optional[Any] = field(default=None, repr=False, compare=False)


# -----------------------------
# Helpers
# -----------------------------
def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_memory(memory_path: Path) -> MemoryStore:
    """Load memory store from pickle file and rebuild FAISS index."""
    if not memory_path.exists():
        raise MemoryError(
            f"No memory file found at {memory_path}. Run init first."
        )
    try:
        with memory_path.open("rb") as f:
            data = pickle.load(f)
    except Exception as e:
        raise MemoryError(f"Failed to load memory file: {e}")

    if isinstance(data, dict):
        store = MemoryStore(
            version=2,
            projects=data.get("projects", {}),
            tasks=data.get("tasks", []),
            embeddings=data.get("embeddings"),
            embedding_metadata=data.get("embedding_metadata", []),
        )
    elif isinstance(data, MemoryStore):
        store = data
    else:
        raise MemoryError(f"Unrecognized memory file format: {type(data)}")

    _build_faiss_index(store)
    return store


def _save_memory(store: MemoryStore, memory_path: Path) -> None:
    """Save memory store with backup."""
    _ensure_parent_dir(memory_path)
    if memory_path.exists():
        backup_path = memory_path.with_suffix(".pkl.backup")
        try:
            import shutil

            shutil.copy2(memory_path, backup_path)
        except Exception:
            pass

    tmp_path = memory_path.with_suffix(memory_path.suffix + ".tmp")
    with tmp_path.open("wb") as f:
        pickle.dump(store, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(memory_path)


def _get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(DEFAULT_MODEL)


def _build_faiss_index(store: MemoryStore) -> None:
    """Build FAISS index from embeddings in memory."""
    if store.embeddings is None or len(store.embeddings) == 0:
        store.faiss_index = None
        return
    dim = store.embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product
    normalized = store.embeddings / np.linalg.norm(store.embeddings, axis=1, keepdims=True)
    index.add(normalized.astype(np.float32))
    store.faiss_index = index


def _search_embeddings(
    query: str, store: MemoryStore, model: SentenceTransformer, top_k: int = 5
) -> List[Tuple[TaskData, float]]:
    """Search tasks using FAISS for semantic similarity."""
    if store.faiss_index is None:
        return []

    query_emb = model.encode([query])[0]
    query_emb = query_emb / np.linalg.norm(query_emb)
    D, I = store.faiss_index.search(np.array([query_emb], dtype=np.float32), top_k)
    results: List[Tuple[TaskData, float]] = []
    for idx, score in zip(I[0], D[0]):
        if idx >= len(store.tasks):
            continue
        task = store.tasks[idx]
        results.append((task, float(score)))
    return results


# -----------------------------
# Commands
# -----------------------------
def cmd_init(args: argparse.Namespace) -> int:
    memory_path = Path(args.memory)
    if memory_path.exists() and not args.force:
        print(f"Memory file already exists at: {memory_path}")
        print("Use --force to reinitialize.")
        return 1
    store = MemoryStore()
    _save_memory(store, memory_path)
    Path(args.projects_root).mkdir(parents=True, exist_ok=True)
    print(f"Initialized memory at: {memory_path}")
    print(f"Projects root: {args.projects_root}")
    print(f"Embedding model: {DEFAULT_MODEL}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    print("Memory-RLM Status")
    print(f"  Memory file: {args.memory}")
    print(f"  Version: {store.version}")
    print(f"  Total projects: {len(store.projects)}")
    print(f"  Total tasks: {len(store.tasks)}")
    print(f"  Embeddings: {len(store.embeddings) if store.embeddings is not None else 0}")
    if store.projects and args.show_projects:
        print("\nProjects:")
        for name, proj in sorted(store.projects.items()):
            print(f"  - {name}: {proj.task_count} tasks")
    if store.tasks and args.show_recent:
        print("\nRecent tasks (last 5):")
        for task in store.tasks[-5:]:
            print(f"  - [{task.project}] {task.task_id}: {task.description[:60]}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    if not store.tasks:
        print("No tasks in memory yet.")
        return 0
    model = _get_embedding_model()
    results = _search_embeddings(args.query, store, model, top_k=args.top_k)
    if not results:
        print("No matching tasks found.")
        return 0
    print(f"Search results for: '{args.query}'\n")
    project_scores: Dict[str, float] = {}
    project_tasks: Dict[str, List[Tuple[TaskData, float]]] = {}
    for task, score in results:
        if task.project not in project_scores:
            project_scores[task.project] = score
            project_tasks[task.project] = []
        else:
            project_scores[task.project] = max(project_scores[task.project], score)
        project_tasks[task.project].append((task, score))
    sorted_projects = sorted(project_scores.items(), key=lambda x: x[1], reverse=True)
    for project, max_score in sorted_projects:
        proj_data = store.projects.get(project)
        task_count = proj_data.task_count if proj_data else 0
        print(f"Project: {project} (similarity: {max_score:.3f}, {task_count} total tasks)")
        for task, score in project_tasks[project]:
            print(f"  [{task.task_id}] {task.description[:80]} (score: {score:.3f})")
        print()
    return 0


def cmd_create_project(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    if args.name in store.projects:
        print(f"Project '{args.name}' already exists.")
        return 1
    project_path = Path(args.projects_root) / args.name
    project_path.mkdir(parents=True, exist_ok=True)
    now = time.time()
    store.projects[args.name] = ProjectData(
        name=args.name,
        created_at=now,
        last_updated=now,
        task_count=0,
        folder_path=str(project_path),
    )
    _save_memory(store, Path(args.memory))
    print(f"Created project: {args.name}")
    print(f"Folder: {project_path}")
    return 0


def cmd_add_task(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    # Ensure project
    if args.project not in store.projects:
        project_path = Path(args.projects_root) / args.project
        project_path.mkdir(parents=True, exist_ok=True)
        now = time.time()
        store.projects[args.project] = ProjectData(
            name=args.project,
            created_at=now,
            last_updated=now,
            task_count=0,
            folder_path=str(project_path),
        )
        print(f"Auto-created project: {args.project}")

    proj = store.projects[args.project]
    task_num = proj.task_count + 1
    files_read = [f.strip() for f in args.files_read.split(",")] if args.files_read else []
    files_created = [f.strip() for f in args.files_created.split(",")] if args.files_created else []
    task_id = f"{args.project}_{task_num:04d}"
    task = TaskData(
        task_id=task_id,
        project=args.project,
        task_num=task_num,
        description=args.description,
        files_read=files_read,
        files_created=files_created,
        output_file=args.output_file,
        timestamp=time.time(),
    )
    # Embedding
    model = _get_embedding_model()
    embedding_text = f"{args.project} {args.description} {' '.join(files_read)}"
    embedding = model.encode([embedding_text])[0].astype(np.float32)
    if store.embeddings is None:
        store.embeddings = np.array([embedding])
        embedding_idx = 0
    else:
        embedding_idx = len(store.embeddings)
        store.embeddings = np.vstack([store.embeddings, embedding])
    task.embedding_idx = embedding_idx
    # Update FAISS
    if store.faiss_index is None:
        _build_faiss_index(store)
    else:
        normalized = embedding / np.linalg.norm(embedding)
        store.faiss_index.add(np.array([normalized], dtype=np.float32))
    store.tasks.append(task)
    proj.task_count = task_num
    proj.last_updated = time.time()
    _save_memory(store, Path(args.memory))
    print(f"Added task: {task_id}")
    print(f"  Description: {args.description}")
    print(f"  Task number: {task_num}")
    print(f"  Output: {args.output_file if args.output_file else '(none)'}")
    return 0


def cmd_project_history(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    if args.project not in store.projects:
        print(f"Project '{args.project}' not found.")
        return 1
    proj = store.projects[args.project]
    project_tasks = [t for t in store.tasks if t.project == args.project]
    if not project_tasks:
        print(f"No tasks found for project '{args.project}'")
        return 0
    print(f"Project: {args.project}")
    print(f"  Created: {time.ctime(proj.created_at)}")
    print(f"  Last updated: {time.ctime(proj.last_updated)}")
    print(f"  Total tasks: {proj.task_count}")
    print(f"  Folder: {proj.folder_path}\n")
    for task in sorted(project_tasks, key=lambda t: t.task_num):
        print(f"[{task.task_id}] {task.description}")
        print(f"  Time: {time.ctime(task.timestamp)}")
        if task.files_read:
            print(f"  Files read: {', '.join(task.files_read)}")
        if task.files_created:
            print(f"  Files created: {', '.join(task.files_created)}")
        if task.output_file:
            print(f"  Output: {task.output_file}")
        print()
    return 0


def cmd_export_json(args: argparse.Namespace) -> int:
    store = _load_memory(Path(args.memory))
    export_data = {
        "version": store.version,
        "projects": {name: asdict(proj) for name, proj in store.projects.items()},
        "tasks": [asdict(task) for task in store.tasks],
        "embedding_count": len(store.embeddings) if store.embeddings is not None else 0,
    }
    out_path = Path(args.output)
    _ensure_parent_dir(out_path)
    out_path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
    print(f"Exported memory to: {out_path}")
    return 0


# -----------------------------
# CLI
# -----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="memory_repl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Persistent memory system for RLM workflows with FAISS semantic search."
    )
    p.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    p.add_argument("--projects-root", default=str(DEFAULT_PROJECTS_ROOT))
    sub = p.add_subparsers(dest="cmd", required=True)

    # init
    pi = sub.add_parser("init")
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_init)

    # status
    ps = sub.add_parser("status")
    ps.add_argument("--show-projects", action="store_true")
    ps.add_argument("--show-recent", action="store_true")
    ps.set_defaults(func=cmd_status)

    # search
    pq = sub.add_parser("search")
    pq.add_argument("--query", required=True)
    pq.add_argument("--top-k", type=int, default=5)
    pq.set_defaults(func=cmd_search)

    # create-project
    pc = sub.add_parser("create-project")
    pc.add_argument("--name", required=True)
    pc.set_defaults(func=cmd_create_project)

    # add-task
    pa = sub.add_parser("add-task")
    pa.add_argument("--project", required=True)
    pa.add_argument("--description", required=True)
    pa.add_argument("--files-read")
    pa.add_argument("--files-created")
    pa.add_argument("--output-file")
    pa.set_defaults(func=cmd_add_task)

    # project-history
    ph = sub.add_parser("project-history")
    ph.add_argument("--project", required=True)
    ph.set_defaults(func=cmd_project_history)

    # export-json
    pe = sub.add_parser("export-json")
    pe.add_argument("--output", required=True)
    pe.set_defaults(func=cmd_export_json)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except MemoryError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
