"""
Capability-Based Security Runtime for ZAP.

Core principle: NO ambient authority. Every resource access requires an explicit capability.
Capabilities are unforgeable, delegatable, and revocable.

Usage:
    rt = CapabilityRuntime(evaluator)
    
    # Create capabilities
    fs_read = rt.capability("filesystem", read=["/data", "/config"])
    fs_write = rt.capability("filesystem", write=["/tmp"])
    db = rt.capability("postgres", queries=["select_users", "insert_order"])
    http = rt.capability("http", domains=["api.stripe.com", "api.github.com"])
    
    # Run untrusted/AI-generated code with ONLY these capabilities
    rt.run_untrusted(ai_generated_code, capabilities=[fs_read, db, http])
    
    # Capabilities can be delegated (attenuated)
    limited_db = db.delegate(queries=["select_users"])  # read-only subset
    rt.run_untrusted(user_plugin, capabilities=[limited_db])
    
    # Revoke at any time
    rt.revoke(fs_write)  # instantly cuts off write access
"""

import os
import json
import uuid
import time
import sqlite3
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable, Union
from pathlib import Path
from abc import ABC, abstractmethod
from contextlib import contextmanager
import threading

from src.values import ZapDict, ZapList, ZapFunction, ZapBuiltin


# =============================================================================
# Capability System Core
# =============================================================================

@dataclass(frozen=True)
class Capability:
    """Unforgeable capability token. Immutable once created."""
    id: str
    resource_type: str      # "filesystem", "network", "database", "process", "env"
    permissions: Dict[str, Any]  # resource-specific permissions
    parent_id: Optional[str] = None  # for delegation chain
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        object.__setattr__(self, '_revoked', False)
    
    @property
    def revoked(self) -> bool:
        return getattr(self, '_revoked', False)
    
    def revoke(self):
        object.__setattr__(self, '_revoked', True)
    
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True
    
    def delegate(self, **restrictions) -> 'Capability':
        """Create a child capability with additional restrictions (attenuation)."""
        if not self.is_valid():
            raise RuntimeError("Cannot delegate revoked/expired capability")
        
        new_perms = {**self.permissions}
        for key, value in restrictions.items():
            if key in new_perms:
                # Intersect permissions (attenuation)
                if isinstance(new_perms[key], list) and isinstance(value, list):
                    new_perms[key] = [v for v in new_perms[key] if v in value]
                elif isinstance(new_perms[key], dict) and isinstance(value, dict):
                    new_perms[key] = {k: v for k, v in new_perms[key].items() if k in value}
                else:
                    new_perms[key] = value
            else:
                new_perms[key] = value
        
        return Capability(
            id=str(uuid.uuid4())[:8],
            resource_type=self.resource_type,
            permissions=new_perms,
            parent_id=self.id,
            expires_at=self.expires_at,
            metadata={"delegated_from": self.id, **restrictions}
        )
    
    def __repr__(self):
        status = "REVOKED" if self.revoked else ("EXPIRED" if self.expires_at and time.time() > self.expires_at else "ACTIVE")
        return f"Capability({self.resource_type}@{self.id[:8]} [{status}])"


class CapabilityRegistry:
    """Central registry for all capabilities in a runtime."""
    
    def __init__(self):
        self._caps: Dict[str, Capability] = {}
        self._revoked: Set[str] = set()
        self._lock = threading.RLock()
    
    def register(self, cap: Capability) -> Capability:
        with self._lock:
            self._caps[cap.id] = cap
            return cap
    
    def get(self, cap_id: str) -> Optional[Capability]:
        with self._lock:
            return self._caps.get(cap_id)
    
    def revoke(self, cap_id: str) -> bool:
        with self._lock:
            cap = self._caps.get(cap_id)
            if cap:
                cap.revoke()
                self._revoked.add(cap_id)
                return True
            return False
    
    def revoke_tree(self, cap_id: str) -> int:
        """Revoke a capability and all its descendants."""
        with self._lock:
            count = 0
            to_revoke = [cap_id]
            for cid, cap in self._caps.items():
                if cap.parent_id in to_revoke:
                    to_revoke.append(cid)
            for cid in to_revoke:
                if cid in self._caps:
                    self._caps[cid].revoke()
                    self._revoked.add(cid)
                    count += 1
            return count
    
    def list_active(self, resource_type: Optional[str] = None) -> List[Capability]:
        with self._lock:
            caps = [c for c in self._caps.values() if c.is_valid()]
            if resource_type:
                caps = [c for c in caps if c.resource_type == resource_type]
            return caps


# =============================================================================
# Resource Guards (Enforce capabilities at access time)
# =============================================================================

class ResourceGuard(ABC):
    """Base class for capability-enforced resource access."""
    
    @abstractmethod
    def check(self, cap: Capability, operation: str, **kwargs) -> bool:
        """Return True if capability allows operation."""
        pass
    
    @abstractmethod
    def wrap(self, cap: Capability) -> Any:
        """Return a proxied resource that enforces the capability."""
        pass


class FileSystemGuard(ResourceGuard):
    """Enforce filesystem capabilities."""
    
    def __init__(self, base_path: str = "/"):
        self.base_path = Path(base_path).resolve()
    
    def _resolve(self, path: str) -> Path:
        p = Path(path).resolve()
        try:
            p.relative_to(self.base_path)
        except ValueError:
            raise PermissionError(f"Path {path} outside base {self.base_path}")
        return p
    
    def check(self, cap: Capability, operation: str, **kwargs) -> bool:
        if not cap.is_valid() or cap.resource_type != "filesystem":
            return False
        path = kwargs.get("path", "")
        
        if operation == "read":
            allowed = cap.permissions.get("read", [])
            return any(self._matches(path, a) for a in allowed)
        elif operation == "write":
            allowed = cap.permissions.get("write", [])
            return any(self._matches(path, a) for a in allowed)
        elif operation == "list":
            allowed = cap.permissions.get("list", cap.permissions.get("read", []))
            return any(self._matches(path, a) for a in allowed)
        return False
    
    def _matches(self, path: str, pattern: str) -> bool:
        try:
            p = self._resolve(path)
            pat = Path(pattern).resolve()
            if pat.is_dir() or pattern.endswith("/") or pattern.endswith("*"):
                return str(p).startswith(str(pat))
            return p == pat
        except (PermissionError, ValueError):
            return False
    
    def wrap(self, cap: Capability) -> 'FileSystemProxy':
        return FileSystemProxy(self, cap)


class FileSystemProxy:
    """Proxy that enforces filesystem capability on every operation."""
    
    def __init__(self, guard: FileSystemGuard, cap: Capability):
        self._guard = guard
        self._cap = cap
    
    def read(self, path: str) -> str:
        if not self._guard.check(self._cap, "read", path=path):
            raise PermissionError(f"No read capability for {path}")
        with open(self._guard._resolve(path), 'r') as f:
            return f.read()
    
    def write(self, path: str, content: str) -> bool:
        if not self._guard.check(self._cap, "write", path=path):
            raise PermissionError(f"No write capability for {path}")
        p = self._guard._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w') as f:
            f.write(content)
        return True
    
    def list(self, path: str) -> List[str]:
        if not self._guard.check(self._cap, "list", path=path):
            raise PermissionError(f"No list capability for {path}")
        return os.listdir(self._guard._resolve(path))
    
    def exists(self, path: str) -> bool:
        if not self._guard.check(self._cap, "read", path=path):
            raise PermissionError(f"No read capability for {path}")
        return self._guard._resolve(path).exists()
    
    def mkdir(self, path: str) -> bool:
        if not self._guard.check(self._cap, "write", path=path):
            raise PermissionError(f"No write capability for {path}")
        self._guard._resolve(path).mkdir(parents=True, exist_ok=True)
        return True


class NetworkGuard(ResourceGuard):
    """Enforce HTTP/Network capabilities."""
    
    def __init__(self):
        self._allowed_domains = set()
    
    def check(self, cap: Capability, operation: str, **kwargs) -> bool:
        if not cap.is_valid() or cap.resource_type != "network":
            return False
        domain = kwargs.get("domain", "")
        allowed = cap.permissions.get("domains", [])
        return any(self._domain_match(domain, d) for d in allowed)
    
    def _domain_match(self, domain: str, pattern: str) -> bool:
        if pattern.startswith("*."):
            return domain.endswith(pattern[1:]) or domain == pattern[2:]
        return domain == pattern
    
    def wrap(self, cap: Capability) -> 'NetworkProxy':
        return NetworkProxy(self, cap)


class NetworkProxy:
    """Proxy that enforces network capability on HTTP requests."""
    
    def __init__(self, guard: NetworkGuard, cap: Capability):
        self._guard = guard
        self._cap = cap
    
    def get(self, url: str, **kwargs) -> Any:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not self._guard.check(self._cap, "GET", domain=domain):
            raise PermissionError(f"No network capability for {domain}")
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')
    
    def post(self, url: str, data: Any = None, **kwargs) -> Any:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not self._guard.check(self._cap, "POST", domain=domain):
            raise PermissionError(f"No network capability for {domain}")
        import urllib.request, json
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, method='POST',
                                      headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')


class DatabaseGuard(ResourceGuard):
    """Enforce database capabilities."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = None
    
    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def check(self, cap: Capability, operation: str, **kwargs) -> bool:
        if not cap.is_valid() or cap.resource_type != "database":
            return False
        query_name = kwargs.get("query", "")
        allowed = cap.permissions.get("queries", [])
        return query_name in allowed
    
    def wrap(self, cap: Capability) -> 'DatabaseProxy':
        return DatabaseProxy(self, cap)


class DatabaseProxy:
    """Proxy that enforces database capability on queries."""
    
    def __init__(self, guard: DatabaseGuard, cap: Capability):
        self._guard = guard
        self._cap = cap
        self._prepared: Dict[str, str] = {}
    
    def prepare(self, name: str, sql: str) -> 'DatabaseProxy':
        """Pre-register a named query (required for capability check)."""
        if not self._guard.check(self._cap, "prepare", query=name):
            raise PermissionError(f"No prepare capability for query '{name}'")
        self._prepared[name] = sql
        return self
    
    def query(self, name: str, params: tuple = ()) -> ZapList:
        if name not in self._prepared:
            raise ValueError(f"Query '{name}' not prepared")
        if not self._guard.check(self._cap, "execute", query=name):
            raise PermissionError(f"No execute capability for query '{name}'")
        
        conn = self._guard._get_conn()
        cursor = conn.execute(self._prepared[name], params)
        rows = [dict(row) for row in cursor.fetchall()]
        return ZapList(rows)
    
    def execute(self, name: str, params: tuple = ()) -> int:
        if name not in self._prepared:
            raise ValueError(f"Query '{name}' not prepared")
        if not self._guard.check(self._cap, "execute", query=name):
            raise PermissionError(f"No execute capability for query '{name}'")
        
        conn = self._guard._get_conn()
        cursor = conn.execute(self._prepared[name], params)
        conn.commit()
        return cursor.rowcount


class ProcessGuard(ResourceGuard):
    """Enforce subprocess/process capabilities."""
    
    def check(self, cap: Capability, operation: str, **kwargs) -> bool:
        if not cap.is_valid() or cap.resource_type != "process":
            return False
        cmd = kwargs.get("command", "")
        allowed = cap.permissions.get("commands", [])
        return any(cmd.startswith(a) for a in allowed)
    
    def wrap(self, cap: Capability) -> 'ProcessProxy':
        return ProcessProxy(self, cap)


class ProcessProxy:
    """Proxy that enforces process capability on subprocess calls."""
    
    def __init__(self, guard: ProcessGuard, cap: Capability):
        self._guard = guard
        self._cap = cap
    
    def run(self, command: List[str], **kwargs) -> Dict:
        if not self._guard.check(self._cap, "run", command=command[0]):
            raise PermissionError(f"No process capability for {command[0]}")
        result = subprocess.run(command, capture_output=True, text=True, **kwargs)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


# =============================================================================
# Capability Runtime (Integration with Evaluator)
# =============================================================================

class CapabilityRuntime:
    """
    Drop-in capability system for ZAP evaluator.
    
    Usage:
        rt = CapabilityRuntime()
        
        # Create capabilities
        fs = rt.capability("filesystem", read=["/data"], write=["/tmp"])
        net = rt.capability("network", domains=["api.stripe.com"])
        db = rt.capability("database", queries=["get_user", "create_order"])
        
        # Run code with ONLY these capabilities
        rt.run_with_capabilities(untrusted_code, [fs, net, db])
    """
    
    def __init__(self, evaluator=None):
        self.evaluator = evaluator
        self.registry = CapabilityRegistry()
        self.guards = {
            "filesystem": FileSystemGuard(),
            "network": NetworkGuard(),
            "database": DatabaseGuard(),
            "process": ProcessGuard(),
        }
        self._current_capabilities: List[Capability] = []
        self._capability_env: Optional[Environment] = None
    
    def capability(self, resource_type: str, **permissions) -> Capability:
        """Create a new capability."""
        cap = Capability(
            id=str(uuid.uuid4())[:8],
            resource_type=resource_type,
            permissions=permissions,
        )
        return self.registry.register(cap)
    
    def revoke(self, cap: Capability) -> bool:
        return self.registry.revoke(cap.id)
    
    def revoke_all_descendants(self, cap: Capability) -> int:
        return self.registry.revoke_tree(cap.id)
    
    def run_with_capabilities(self, source: str, capabilities: List[Capability]) -> Any:
        """Execute source code with ONLY the given capabilities."""
        if not self.evaluator:
            from src.evaluator import Evaluator
            from src.parser import Parser
            from src.lexer import Lexer
            evaluator = Evaluator()
            tokens = Lexer(source, '<capability>').tokenize()
            ast = Parser(tokens).parse()
        else:
            evaluator = self.evaluator
            from src.parser import Parser
            from src.lexer import Lexer
            tokens = Lexer(source, '<capability>').tokenize()
            ast = Parser(tokens).parse()
        
        # Build capability environment
        cap_env = self._build_capability_env(capabilities)
        
        # Swap environment
        old_env = evaluator.env
        evaluator.env = cap_env
        try:
            return evaluator.evaluate(ast)
        finally:
            evaluator.env = old_env
    
    def _build_capability_env(self, capabilities: List[Capability]) -> 'Environment':
        """Create an environment with capability-wrapped resources."""
        from src.environment import Environment
        from src.values import ZapBuiltin
        
        env = Environment()
        
        # Register each capability as a builtin
        for cap in capabilities:
            if not cap.is_valid():
                continue
            
            guard = self.guards.get(cap.resource_type)
            if not guard:
                continue
            
            proxy = guard.wrap(cap)
            
            # Expose proxy methods as builtins
            if cap.resource_type == "filesystem":
                env.define("fs_read", ZapBuiltin(lambda p: proxy.read(p), "fs_read"))
                env.define("fs_write", ZapBuiltin(lambda p, c: proxy.write(p, c), "fs_write"))
                env.define("fs_list", ZapBuiltin(lambda p: ZapList(proxy.list(p)), "fs_list"))
                env.define("fs_exists", ZapBuiltin(lambda p: proxy.exists(p), "fs_exists"))
                env.define("fs_mkdir", ZapBuiltin(lambda p: proxy.mkdir(p), "fs_mkdir"))
            
            elif cap.resource_type == "network":
                env.define("http_get", ZapBuiltin(lambda u: proxy.get(u), "http_get"))
                env.define("http_post", ZapBuiltin(lambda u, d=None: proxy.post(u, d), "http_post"))
            
            elif cap.resource_type == "database":
                # Need to register queries first
                def make_query(name):
                    return ZapBuiltin(lambda *args: proxy.query(name, args), f"db_{name}")
                def make_execute(name):
                    return ZapBuiltin(lambda *args: proxy.execute(name, args), f"db_exec_{name}")
                
                for qname in cap.permissions.get("queries", []):
                    env.define(f"db_{qname}", make_query(qname))
                    env.define(f"db_exec_{qname}", make_execute(qname))
            
            elif cap.resource_type == "process":
                env.define("proc_run", ZapBuiltin(lambda *cmd: proxy.run(list(cmd)), "proc_run"))
        
        # Store capability references for introspection
        env.define("__capabilities__", ZapList([
            ZapDict({
                "id": c.id,
                "type": c.resource_type,
                "permissions": c.permissions,
                "valid": c.is_valid()
            }) for c in capabilities
        ]))
        
        return env
    
    def list_capabilities(self, resource_type: Optional[str] = None) -> List[Capability]:
        return self.registry.list_active(resource_type)


# =============================================================================
# Builtin Integration (Add to make_zap_builtins)
# =============================================================================

def _stdlib_capability(resource_type: str, **perms):
    """Create a capability from Zap code."""
    # This would be called from within a capability-enabled evaluator
    # For now, return a representation
    return ZapDict({
        "type": resource_type,
        "permissions": perms,
        "note": "Use capability_runtime to create real capabilities"
    })

def _stdlib_fs_cap(read: list = None, write: list = None, list_dirs: list = None):
    """Filesystem capability: fs_cap(read=["/data"], write=["/tmp"])"""
    perms = {}
    if read: perms["read"] = read
    if write: perms["write"] = write
    if list_dirs: perms["list"] = list_dirs
    return _stdlib_capability("filesystem", **perms)

def _stdlib_net_cap(domains: list):
    """Network capability: net_cap(domains=["api.stripe.com"])"""
    return _stdlib_capability("network", domains=domains)

def _stdlib_db_cap(queries: list):
    """Database capability: db_cap(queries=["get_user", "create_order"])"""
    return _stdlib_capability("database", queries=queries)

def _stdlib_proc_cap(commands: list):
    """Process capability: proc_cap(commands=["python", "node"])"""
    return _stdlib_capability("process", commands=commands)

def _stdlib_delegate(cap: ZapDict, **restrictions):
    """Delegate/attenuate a capability: delegate(fs_cap, read=["/public"])"""
    # In real implementation, would unwrap cap and create child
    return ZapDict({
        "delegated_from": cap.get("id", "unknown"),
        "restrictions": restrictions,
        "note": "Use CapabilityRuntime.delegate() for real delegation"
    })


# Export for make_zap_builtins integration
CAPABILITY_BUILTINS = {
    'fs_cap': _stdlib_fs_cap,
    'net_cap': _stdlib_net_cap,
    'db_cap': _stdlib_db_cap,
    'proc_cap': _stdlib_proc_cap,
    'delegate': _stdlib_delegate,
}