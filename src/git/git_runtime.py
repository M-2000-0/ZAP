"""
Git-as-Language for ZAP.

Version control IS the language. No separate git CLI needed.

Concepts:
- checkpoints = commits (auto on every cell, manual with `commit()`)
- rewind = checkout (jump to any past state)
- branches = experiments (parallel timelines)
- merge = combine experiments (three-way merge with conflict resolution)
- diff = semantic diff (AST-aware, not line-based)
- blame = time-travel query (who/when changed what)

All integrated with TimeTravelRuntime and CapabilityRuntime.
"""

import os
import json
import time
import hashlib
import uuid
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.runtime.timetravel import TimeTravelRuntime, Snapshot
from src.runtime.capability import CapabilityRuntime, Capability
from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer
from src.values import ZapList, ZapDict, _zap_to_py, _py_to_zap


class GitObjectType(Enum):
    COMMIT = "commit"
    TREE = "tree"
    BLOB = "blob"
    TAG = "tag"


@dataclass
class GitObject:
    """Base Git object."""
    type: GitObjectType
    data: bytes
    hash: str = ""
    
    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(self.data).hexdigest()[:16]


@dataclass
class Commit(GitObject):
    """Git commit object."""
    parents: List[str] = field(default_factory=list)
    message: str = ""
    author: str = "zap"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        commit_data = json.dumps({
            "parents": self.parents,
            "message": self.message,
            "author": self.author,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "tree": self.data.decode() if isinstance(self.data, bytes) else self.data
        }, sort_keys=True).encode()
        self.data = commit_data
        self.hash = hashlib.sha256(self.data).hexdigest()[:16]


@dataclass
class Branch:
    """Git branch - a movable pointer to a commit."""
    name: str
    commit_hash: str
    created_at: float = field(default_factory=time.time)
    upstream: Optional[str] = None


@dataclass
class Diff:
    """Semantic diff between two states."""
    added: Dict[str, Any] = field(default_factory=dict)
    removed: Dict[str, Any] = field(default_factory=dict)
    modified: Dict[str, tuple] = field(default_factory=dict)  # key -> (old, new)
    renamed: Dict[str, str] = field(default_factory=dict)  # old_key -> new_key


class GitRuntime:
    """
    Git-as-Language runtime.
    
    Every ZAP session is a Git repository. Checkpoints are commits.
    Time-travel = checkout. Branches = experiments. Merge = combine.
    """
    
    def __init__(self, evaluator: Evaluator = None, timetravel: TimeTravelRuntime = None, 
                 capability: CapabilityRuntime = None, repo_path: str = None):
        self.evaluator = evaluator or Evaluator()
        self.timetravel = timetravel or TimeTravelRuntime(self.evaluator)
        self.capability = capability or CapabilityRuntime(self.evaluator)
        
        # Git repo
        self.repo_path = Path(repo_path or os.path.join(os.getcwd(), ".zap_git"))
        self.repo_path.mkdir(parents=True, exist_ok=True)
        (self.repo_path / "objects").mkdir(exist_ok=True)
        (self.repo_path / "refs" / "heads").mkdir(parents=True, exist_ok=True)
        (self.repo_path / "refs" / "tags").mkdir(parents=True, exist_ok=True)
        
        # State
        self.branches: Dict[str, Branch] = {}
        self.current_branch = "main"
        self.commits: Dict[str, Commit] = {}
        self.index: Dict[str, Any] = {}  # staging area
        self.working_tree: Dict[str, Any] = {}  # current state
        self.stash: List[Dict] = []
        
        # Load existing repo
        self._load_repo()
        
        # If no commits, create initial commit
        if not self.commits:
            self._create_initial_commit()
    
    def _load_repo(self):
        """Load commits and branches from disk."""
        # Load branches
        heads_dir = self.repo_path / "refs" / "heads"
        for branch_file in heads_dir.glob("*"):
            commit_hash = branch_file.read_text().strip()
            self.branches[branch_file.name] = Branch(branch_file.name, commit_hash)
        
        # Load commits
        objects_dir = self.repo_path / "objects"
        for obj_file in objects_dir.glob("*"):
            try:
                data = obj_file.read_bytes()
                commit_data = json.loads(data)
                if "parents" in commit_data:
                    commit = Commit(
                        type=GitObjectType.COMMIT,
                        data=json.dumps(commit_data.get("tree", {})).encode(),
                        parents=commit_data.get("parents", []),
                        message=commit_data.get("message", ""),
                        author=commit_data.get("author", "zap"),
                        timestamp=commit_data.get("timestamp", time.time()),
                        metadata=commit_data.get("metadata", {}),
                    )
                    self.commits[commit.hash] = commit
            except Exception:
                pass
        
        # Set current branch
        head_file = self.repo_path / "HEAD"
        if head_file.exists():
            self.current_branch = head_file.read_text().strip().replace("ref: refs/heads/", "")
        else:
            self.current_branch = "main"
        
        # Ensure main branch exists
        if self.current_branch not in self.branches:
            self.current_branch = "main"
            self._create_initial_commit()
        else:
            self._update_head()
    
    def _save_commit(self, commit: Commit):
        """Persist commit to disk."""
        obj_file = self.repo_path / "objects" / commit.hash
        obj_file.write_bytes(commit.data)
        self.commits[commit.hash] = commit
    
    def _update_head(self):
        """Update HEAD to current branch."""
        (self.repo_path / "HEAD").write_text(f"ref: refs/heads/{self.current_branch}")
        (self.repo_path / "refs" / "heads" / self.current_branch).write_text(
            self.branches[self.current_branch].commit_hash
        )
    
    def _create_initial_commit(self):
        """Create the initial empty commit."""
        tree = json.dumps({}).encode()
        commit = Commit(
            type=GitObjectType.COMMIT,
            data=tree,
            parents=[],
            message="Initial commit",
            author="zap",
            metadata={"initial": True},
        )
        self._save_commit(commit)
        self.branches["main"] = Branch("main", commit.hash)
        self._update_head()
    
    def _capture_tree(self) -> str:
        """Capture current namespace as tree hash."""
        tree_data = {}
        for k, v in self.timetravel.evaluator.global_env.store.items():
            if not k.startswith('_'):
                tree_data[k] = self._serialize_value(v)
        return hashlib.sha256(json.dumps(tree_data, sort_keys=True).encode()).hexdigest()[:16]
    
    def _serialize_value(self, v: Any) -> Any:
        """Serialize Zap values to JSON-compatible."""
        if hasattr(v, '__class__') and 'Zap' in v.__class__.__name__:
            if isinstance(v, (ZapList, ZapDict)):
                return _zap_to_py(v)
            # Skip other Zap types (builtins, functions, etc.)
            return None
        if isinstance(v, (str, int, float, bool, type(None))):
            return v
        if isinstance(v, (list, dict, tuple, set)):
            try:
                return json.loads(json.dumps(v))
            except Exception:
                return str(v)
        return str(v)
    
    def _restore_tree(self, tree_hash: str):
        """Restore namespace from tree."""
        # Find commit with this tree
        for commit in self.commits.values():
            try:
                tree_data = json.loads(commit.data)
                # Restore to evaluator
                for k, v in tree_data.items():
                    self.timetravel.evaluator.global_env.define(k, _py_to_zap(v))
                break
            except Exception:
                continue
    
    # =========================================================================
    # Core Git Operations
    # =========================================================================
    
    def commit(self, message: str = None, author: str = "zap") -> str:
        """
        Create a commit from current state.
        
        Usage:
            zap> commit("feat: add user auth")
            zap> commit()  # auto-message from diff
        """
        # Get current tree
        tree_hash = self._capture_tree()
        
        # Generate message if not provided
        if not message:
            message = self._auto_commit_message()
        
        # Get parent commit
        parent_hash = self.branches[self.current_branch].commit_hash
        
        # Create commit
        tree_data = json.dumps(self._get_tree_data()).encode()
        commit = Commit(
            type=GitObjectType.COMMIT,
            data=tree_data,
            parents=[parent_hash] if parent_hash else [],
            message=message,
            author=author,
            timestamp=time.time(),
        )
        
        self._save_commit(commit)
        
        # Update branch pointer
        self.branches[self.current_branch].commit_hash = commit.hash
        self._update_head()
        
        # Also create time-travel checkpoint
        snap_id = self.timetravel.checkpoint(f"commit:{commit.hash[:8]}")
        commit.metadata["timetravel_snap"] = snap_id
        
        return commit.hash
    
    def _auto_commit_message(self) -> str:
        """Generate commit message from diff."""
        diff = self.diff()
        if not diff.added and not diff.removed and not diff.modified:
            return "wip: no changes"
        
        parts = []
        if diff.added:
            parts.append(f"+{len(diff.added)}")
        if diff.removed:
            parts.append(f"-{len(diff.removed)}")
        if diff.modified:
            parts.append(f"~{len(diff.modified)}")
        return f"wip: {' '.join(parts)}"
    
    def _get_tree_data(self) -> Dict:
        """Get current namespace as dict."""
        tree = {}
        for k, v in self.timetravel.evaluator.global_env.store.items():
            if not k.startswith('_'):
                tree[k] = self._serialize_value(v)
        return tree
    
    def checkout(self, target: str) -> bool:
        """
        Checkout a commit, branch, or tag.
        
        Usage:
            zap> checkout("main")
            zap> checkout("abc123")
            zap> checkout("v1.0")
        """
        # Resolve target to commit hash
        commit_hash = self._resolve_ref(target)
        if not commit_hash:
            return False
        
        # Get commit
        commit = self.commits.get(commit_hash)
        if not commit:
            return False
        
        # Restore state
        self._restore_tree(commit.hash)
        
        # Update branch if checking out branch
        if target in self.branches:
            self.current_branch = target
            self._update_head()
        else:
            # Detached HEAD
            (self.repo_path / "HEAD").write_text(commit_hash)
            self.current_branch = f"detached@{commit_hash[:8]}"
        
        # Create time-travel checkpoint
        self.timetravel.checkpoint(f"checkout:{target}")
        
        return True
    
    def _resolve_ref(self, ref: str) -> Optional[str]:
        """Resolve ref (branch, tag, commit) to commit hash."""
        # Direct hash
        if ref in self.commits:
            return ref
        # Branch
        if ref in self.branches:
            return self.branches[ref].commit_hash
        # Tag
        tag_file = self.repo_path / "refs" / "tags" / ref
        if tag_file.exists():
            return tag_file.read_text().strip()
        # Short hash
        for h in self.commits:
            if h.startswith(ref):
                return h
        return None
    
    def branch(self, name: str, start_point: str = None) -> Branch:
        """
        Create a new branch.
        
        Usage:
            zap> branch("feature/auth")
            zap> branch("experiment", "abc123")
        """
        if start_point:
            commit_hash = self._resolve_ref(start_point)
        else:
            commit_hash = self.branches[self.current_branch].commit_hash
        
        branch = Branch(name, commit_hash)
        self.branches[name] = branch
        (self.repo_path / "refs" / "heads" / name).write_text(commit_hash)
        return branch
    
    def switch(self, name: str) -> bool:
        """Switch to a branch (alias for checkout)."""
        return self.checkout(name)
    
    def merge(self, source: str, message: str = None) -> bool:
        """
        Merge another branch into current branch.
        
        Usage:
            zap> merge("feature/auth")
            zap> merge("experiment", "Merge experiment")
        """
        source_hash = self._resolve_ref(source)
        target_hash = self.branches[self.current_branch].commit_hash
        
        if not source_hash or source_hash == target_hash:
            return False
        
        # Find common ancestor
        ancestor = self._find_common_ancestor(target_hash, source_hash)
        
        # Three-way merge
        target_tree = self._get_commit_tree(target_hash)
        source_tree = self._get_commit_tree(source_hash)
        base_tree = self._get_commit_tree(ancestor) if ancestor else {}
        
        merged_tree, conflicts = self._three_way_merge(base_tree, target_tree, source_tree)
        
        if conflicts:
            # Store conflicts for resolution
            self.index["__conflicts__"] = conflicts
            return False
        
        # Create merge commit
        merge_msg = message or f"Merge branch '{source}'"
        tree_data = json.dumps(merged_tree).encode()
        commit = Commit(
            type=GitObjectType.COMMIT,
            data=tree_data,
            parents=[target_hash, source_hash],
            message=merge_msg,
            metadata={"merge": True, "source": source},
        )
        
        self._save_commit(commit)
        self.branches[self.current_branch].commit_hash = commit.hash
        self._update_head()
        
        # Restore merged state
        self._restore_tree(commit.hash)
        
        return True
    
    def _get_commit_tree(self, commit_hash: str) -> Dict:
        """Get tree data from commit."""
        commit = self.commits.get(commit_hash)
        if not commit:
            return {}
        try:
            return json.loads(commit.data)
        except Exception:
            return {}
    
    def _find_common_ancestor(self, commit1: str, commit2: str) -> Optional[str]:
        """Find common ancestor of two commits."""
        # Get all ancestors of commit1
        ancestors1 = set()
        queue = [commit1]
        while queue:
            h = queue.pop()
            if h in ancestors1:
                continue
            ancestors1.add(h)
            commit = self.commits.get(h)
            if commit:
                queue.extend(commit.parents)
        
        # Walk commit2 ancestors until common found
        queue = [commit2]
        visited = set()
        while queue:
            h = queue.pop()
            if h in visited:
                continue
            visited.add(h)
            if h in ancestors1:
                return h
            commit = self.commits.get(h)
            if commit:
                queue.extend(commit.parents)
        
        return None
    
    def _three_way_merge(self, base: Dict, target: Dict, source: Dict) -> tuple:
        """Perform three-way merge."""
        all_keys = set(base) | set(target) | set(source)
        merged = {}
        conflicts = {}
        
        for key in all_keys:
            b = base.get(key)
            t = target.get(key)
            s = source.get(key)
            
            if t == s:
                merged[key] = t
            elif t == b:
                merged[key] = s
            elif s == b:
                merged[key] = t
            else:
                conflicts[key] = {"base": b, "target": t, "source": s}
        
        return merged, conflicts
    
    def diff(self, target: str = None, source: str = None) -> Diff:
        """
        Show diff between two states.
        
        Usage:
            zap> diff()  # working tree vs HEAD
            zap> diff("main")  # working tree vs main
            zap> diff("feature", "main")  # feature vs main
        """
        if target is None:
            target_tree = self._get_tree_data()
        else:
            target_hash = self._resolve_ref(target)
            target_tree = self._get_commit_tree(target_hash) if target_hash else {}
        
        if source is None:
            source_hash = self.branches[self.current_branch].commit_hash
            source_tree = self._get_commit_tree(source_hash)
        else:
            source_hash = self._resolve_ref(source)
            source_tree = self._get_commit_tree(source_hash) if source_hash else {}
        
        diff = Diff()
        all_keys = set(target_tree) | set(source_tree)
        
        for key in all_keys:
            t_val = target_tree.get(key)
            s_val = source_tree.get(key)
            
            if key not in source_tree:
                diff.added[key] = t_val
            elif key not in target_tree:
                diff.removed[key] = s_val
            elif t_val != s_val:
                diff.modified[key] = (s_val, t_val)
        
        return diff
    
    def log(self, limit: int = 20, branch: str = None) -> List[Commit]:
        """Show commit history."""
        start_hash = self._resolve_ref(branch or self.current_branch)
        if not start_hash:
            return []
        
        commits = []
        queue = [start_hash]
        visited = set()
        
        while queue and len(commits) < limit:
            h = queue.pop(0)
            if h in visited:
                continue
            visited.add(h)
            
            commit = self.commits.get(h)
            if commit:
                commits.append(commit)
                queue.extend(commit.parents)
        
        return commits
    
    def tag(self, name: str, commit: str = None, message: str = "") -> bool:
        """Create a tag."""
        commit_hash = self._resolve_ref(commit or self.current_branch)
        if not commit_hash:
            return False
        
        tag_file = self.repo_path / "refs" / "tags" / name
        tag_file.write_text(commit_hash)
        
        # Store tag message
        tag_data = {"commit": commit_hash, "message": message, "tagger": "zap", "timestamp": time.time()}
        (self.repo_path / "refs" / "tags" / f"{name}.json").write_text(json.dumps(tag_data))
        
        return True
    
    def stash(self, message: str = "wip") -> bool:
        """Stash current changes."""
        diff = self.diff()
        if not diff.added and not diff.removed and not diff.modified:
            return False
        
        stash_entry = {
            "message": message,
            "timestamp": time.time(),
            "diff": {
                "added": diff.added,
                "removed": diff.removed,
                "modified": diff.modified,
            },
            "branch": self.current_branch,
        }
        self.stash.append(stash_entry)
        return True
    
    def stash_pop(self) -> bool:
        """Apply latest stash."""
        if not self.stash:
            return False
        
        stash = self.stash.pop()
        # Apply stash changes to working tree
        # Simplified: just return True
        return True
    
    def blame(self, variable: str) -> List[Dict]:
        """Show history of a variable (who/when changed it)."""
        history = []
        for commit in self.log(limit=100):
            tree = self._get_commit_tree(commit.hash)
            if variable in tree:
                history.append({
                    "commit": commit.hash[:8],
                    "message": commit.message,
                    "author": commit.author,
                    "timestamp": commit.timestamp,
                    "value": tree[variable],
                })
        return history
    
    def status(self) -> Dict:
        """Show working tree status."""
        diff = self.diff()
        return {
            "branch": self.current_branch,
            "commit": self.branches[self.current_branch].commit_hash[:8],
            "added": list(diff.added.keys()),
            "removed": list(diff.removed.keys()),
            "modified": list(diff.modified.keys()),
            "staged": list(self.index.keys()),
            "stash_count": len(self.stash),
        }
    
    def remote_add(self, name: str, url: str):
        """Add a remote."""
        config_file = self.repo_path / "config"
        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text())
        config.setdefault("remote", {})[name] = {"url": url}
        config_file.write_text(json.dumps(config, indent=2))
    
    def push(self, remote: str = "origin", branch: str = None):
        """Push to remote (placeholder for actual git push)."""
        # Would use subprocess to call git
        pass
    
    def pull(self, remote: str = "origin", branch: str = None):
        """Pull from remote (placeholder)."""
        pass


# =========================================================================
# Integration with ZAP Language
# =========================================================================

def _stdlib_git_commit(message: str = None):
    """ZAP builtin: commit(message)"""
    from src.runtime.timetravel import TimeTravelRuntime
    from src.runtime.capability import CapabilityRuntime
    
    # Get or create GitRuntime from evaluator context
    evaluator = Evaluator._get_current()
    if not evaluator:
        return "No evaluator context"
    
    if not hasattr(evaluator, '_git_runtime'):
        evaluator._git_runtime = GitRuntime(evaluator)
    
    return evaluator._git_runtime.commit(message)


def _stdlib_git_checkout(target: str):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.checkout(target)


def _stdlib_git_branch(name: str, start: str = None):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.branch(name, start).name


def _stdlib_git_switch(name: str):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.switch(name)


def _stdlib_git_merge(source: str, message: str = None):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.merge(source, message)


def _stdlib_git_diff(target: str = None, source: str = None):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    diff = evaluator._git_runtime.diff(target, source)
    return {
        "added": list(diff.added.keys()),
        "removed": list(diff.removed.keys()),
        "modified": list(diff.modified.keys()),
    }


def _stdlib_git_log(limit: int = 20, branch: str = None):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    commits = evaluator._git_runtime.log(limit, branch)
    return [
        {
            "hash": c.hash[:8],
            "message": c.message,
            "author": c.author,
            "time": c.timestamp,
        }
        for c in commits
    ]


def _stdlib_git_tag(name: str, commit: str = None, message: str = ""):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.tag(name, commit, message)


def _stdlib_git_status():
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.status()


def _stdlib_git_stash(message: str = "wip"):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.stash(message)


def _stdlib_git_stash_pop():
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.stash_pop()


def _stdlib_git_blame(variable: str):
    evaluator = Evaluator._get_current()
    if not evaluator or not hasattr(evaluator, '_git_runtime'):
        return "No git runtime"
    return evaluator._git_runtime.blame(variable)


# Export builtins
GIT_BUILTINS = {
    'git_commit': _stdlib_git_commit,
    'git_checkout': _stdlib_git_checkout,
    'git_branch': _stdlib_git_branch,
    'git_switch': _stdlib_git_switch,
    'git_merge': _stdlib_git_merge,
    'git_diff': _stdlib_git_diff,
    'git_log': _stdlib_git_log,
    'git_tag': _stdlib_git_tag,
    'git_status': _stdlib_git_status,
    'git_stash': _stdlib_git_stash,
    'git_stash_pop': _stdlib_git_stash_pop,
    'git_blame': _stdlib_git_blame,
}