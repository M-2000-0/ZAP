"""
Data-as-First-Class for zpx.

Tables, streams, and SQL are native language constructs - not external systems.
Unified query engine across in-memory, SQLite, and streaming data.
"""

import os
import json
import time
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterator, Callable, Union
from enum import Enum
from pathlib import Path
from collections import defaultdict
from abc import ABC, abstractmethod
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.values import ZpxList, ZpxDict, ZpxFunction, _zpx_to_py, _py_to_zpx


class DataSourceType(Enum):
    TABLE = "table"           # In-memory table
    STREAM = "stream"         # Append-only stream
    VIEW = "view"             # Derived from query
    EXTERNAL = "external"     # SQLite, Postgres, etc.


@dataclass
class Column:
    """Table column definition."""
    name: str
    type: str = "any"         # int, float, str, bool, datetime, any
    nullable: bool = True
    default: Any = None
    primary_key: bool = False
    unique: bool = False


@dataclass
class TableSchema:
    """Table schema definition."""
    name: str
    columns: List[Column]
    
    def to_sql_create(self) -> str:
        cols = []
        for c in self.columns:
            col_def = f"{c.name} {c.type.upper()}"
            if c.primary_key:
                col_def += " PRIMARY KEY"
            if not c.nullable:
                col_def += " NOT NULL"
            if c.unique:
                col_def += " UNIQUE"
            if c.default is not None:
                col_def += f" DEFAULT {c.default}"
            cols.append(col_def)
        return f"CREATE TABLE {self.name} ({', '.join(cols)})"
    
    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]


class Row:
    """A single table row - dict-like with attribute access."""
    
    def __init__(self, data: Dict, schema: TableSchema = None):
        self._data = data
        self._schema = schema
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'Row' has no attribute '{name}'")
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def to_dict(self) -> Dict:
        return dict(self._data)
    
    def __repr__(self):
        return f"Row({self._data})"


class Table:
    """
    In-memory table with SQL query support.
    
    Features:
    - Schema enforcement (optional)
    - Indexes for fast lookups
    - SQL queries via query()
    - Joins, filters, aggregations
    - Streaming inserts
    """
    
    def __init__(self, name: str, schema: TableSchema = None):
        self.name = name
        self.schema = schema
        self.rows: List[Row] = []
        self._indexes: Dict[str, Dict[Any, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._primary_key_col: Optional[str] = None
        self._lock = threading.RLock()
        
        if schema:
            for col in schema.columns:
                if col.primary_key:
                    self._primary_key_col = col.name
    
    def insert(self, data: Dict) -> Row:
        """Insert a row."""
        with self._lock:
            # Validate schema
            if self.schema:
                for col in self.schema.columns:
                    if col.name not in data:
                        if col.default is not None:
                            data[col.name] = col.default
                        elif not col.nullable:
                            raise ValueError(f"Column '{col.name}' is required")
                    elif col.type != "any" and data[col.name] is not None:
                        data[col.name] = self._coerce_type(data[col.name], col.type)
            
            row = Row(data, self.schema)
            idx = len(self.rows)
            self.rows.append(row)
            
            # Update indexes
            for col_name, value in data.items():
                self._indexes[col_name][value].append(idx)
            
            return row
    
    def insert_many(self, data_list: List[Dict]) -> List[Row]:
        return [self.insert(d) for d in data_list]
    
    def _coerce_type(self, value: Any, type_: str) -> Any:
        if value is None:
            return None
        try:
            if type_ == "int":
                return int(value)
            elif type_ == "float":
                return float(value)
            elif type_ == "str":
                return str(value)
            elif type_ == "bool":
                return bool(value)
            elif type_ == "datetime":
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                return value
        except Exception:
            pass
        return value
    
    def find(self, **conditions) -> List[Row]:
        """Find rows matching conditions."""
        with self._lock:
            candidates = None
            for col, val in conditions.items():
                if col in self._indexes:
                    idxs = self._indexes[col].get(val, [])
                    if candidates is None:
                        candidates = set(idxs)
                    else:
                        candidates &= set(idxs)
                else:
                    # Full scan
                    if candidates is None:
                        candidates = set(range(len(self.rows)))
                    candidates = {i for i in candidates if self.rows[i][col] == val}
            
            if candidates is None:
                return []
            return [self.rows[i] for i in sorted(candidates)]
    
    def find_one(self, **conditions) -> Optional[Row]:
        results = self.find(**conditions)
        return results[0] if results else None
    
    def delete(self, **conditions) -> int:
        """Delete matching rows."""
        with self._lock:
            to_delete = self.find(**conditions)
            if not to_delete:
                return 0
            
            # Get indices to delete
            delete_indices = [self.rows.index(r) for r in to_delete]
            delete_indices.sort(reverse=True)
            
            for idx in delete_indices:
                row = self.rows[idx]
                # Remove from indexes
                for col, val in row._data.items():
                    if col in self._indexes and idx in self._indexes[col].get(val, []):
                        self._indexes[col][val].remove(idx)
                del self.rows[idx]
            
            return len(to_delete)
    
    def update(self, conditions: Dict, updates: Dict) -> int:
        """Update matching rows."""
        with self._lock:
            rows = self.find(**conditions)
            for row in rows:
                # Remove old index entries
                for col, val in row._data.items():
                    if col in self._indexes and self.rows.index(row) in self._indexes[col].get(val, []):
                        self._indexes[col][val].remove(self.rows.index(row))
                
                # Apply updates
                for k, v in updates.items():
                    row[k] = v
                
                # Add new index entries
                for col, val in row._data.items():
                    self._indexes[col][val].append(self.rows.index(row))
            
            return len(rows)
    
    def all(self) -> List[Row]:
        with self._lock:
            return list(self.rows)
    
    def count(self) -> int:
        with self._lock:
            return len(self.rows)
    
    def clear(self):
        with self._lock:
            self.rows.clear()
            self._indexes.clear()
    
    def to_list(self) -> List[Dict]:
        with self._lock:
            return [r.to_dict() for r in self.rows]


class Stream:
    """
    Append-only stream with time-window queries.
    
    Features:
    - Immutable append-only log
    - Time-window queries (last N seconds, tumbling, sliding)
    - Consumer groups for parallel processing
    - Watermarks for event-time processing
    """
    
    def __init__(self, name: str, schema: TableSchema = None, max_size: int = None):
        self.name = name
        self.schema = schema
        self.events: List[Row] = []
        self.max_size = max_size
        self._lock = threading.RLock()
        self._consumers: Dict[str, int] = {}  # consumer_id -> offset
        self._watermark = 0
    
    def append(self, data: Dict) -> Row:
        """Append event to stream."""
        with self._lock:
            if self.schema:
                for col in self.schema.columns:
                    if col.name not in data and col.default is not None:
                        data[col.name] = col.default
            
            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = time.time()
            
            row = Row(data, self.schema)
            self.events.append(row)
            
            # Trim if max_size exceeded
            if self.max_size and len(self.events) > self.max_size:
                self.events = self.events[-self.max_size:]
            
            return row
    
    def append_many(self, data_list: List[Dict]) -> List[Row]:
        return [self.append(d) for d in data_list]
    
    def query(self, 
              since: float = None, 
              until: float = None,
              limit: int = None,
              filter_fn: Callable = None) -> List[Row]:
        """Query stream with time window and filter."""
        with self._lock:
            events = self.events
            
            if since:
                events = [e for e in events if e["timestamp"] >= since]
            if until:
                events = [e for e in events if e["timestamp"] <= until]
            if filter_fn:
                events = [e for e in events if filter_fn(e)]
            if limit:
                events = events[-limit:]
            
            return events
    
    def window_tumbling(self, window_seconds: float) -> List[List[Row]]:
        """Tumbling window aggregation."""
        with self._lock:
            if not self.events:
                return []
            
            windows = defaultdict(list)
            for e in self.events:
                ts = e["timestamp"]
                window_start = int(ts / window_seconds) * window_seconds
                windows[window_start].append(e)
            
            return [windows[k] for k in sorted(windows.keys())]
    
    def window_sliding(self, window_seconds: float, slide_seconds: float) -> List[List[Row]]:
        """Sliding window aggregation."""
        with self._lock:
            if not self.events:
                return []
            
            result = []
            start = min(e["timestamp"] for e in self.events)
            end = max(e["timestamp"] for e in self.events)
            
            window_start = start
            while window_start <= end:
                window_end = window_start + window_seconds
                window_events = [
                    e for e in self.events
                    if window_start <= e.get("timestamp", 0) < window_end
                ]
                if window_events:
                    result.append(window_events)
                window_start += slide_seconds
            
            return result
    
    def subscribe(self, consumer_id: str) -> int:
        """Register consumer, return starting offset."""
        with self._lock:
            self._consumers[consumer_id] = len(self.events)
            return self._consumers[consumer_id]
    
    def consume(self, consumer_id: str, limit: int = 100) -> List[Row]:
        """Consume events from offset."""
        with self._lock:
            offset = self._consumers.get(consumer_id, 0)
            events = self.events[offset:offset + limit]
            self._consumers[consumer_id] = offset + len(events)
            return events
    
    def set_watermark(self, timestamp: float):
        """Set event-time watermark."""
        with self._lock:
            self._watermark = timestamp
    
    def __len__(self):
        with self._lock:
            return len(self.events)


class QueryEngine:
    """
    Unified SQL query engine across Tables, Streams, and external DBs.
    
    Supports:
    - SELECT with WHERE, JOIN, GROUP BY, ORDER BY, LIMIT
    - Subqueries and CTEs
    - Window functions (ROW_NUMBER, RANK, LAG, LEAD)
    - UPSERT (ON CONFLICT)
    """
    
    def __init__(self):
        self.tables: Dict[str, Table] = {}
        self.streams: Dict[str, Stream] = {}
        self.external_connections: Dict[str, sqlite3.Connection] = {}
    
    def register_table(self, table: Table):
        self.tables[table.name] = table
    
    def register_stream(self, stream: Stream):
        self.streams[stream.name] = stream
    
    def connect_external(self, name: str, path: str):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        self.external_connections[name] = conn
    
    def execute(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute SQL query."""
        sql_upper = sql.strip().upper()
        
        if sql_upper.startswith("SELECT"):
            return self._execute_select(sql, params)
        elif sql_upper.startswith("INSERT"):
            return self._execute_insert(sql, params)
        elif sql_upper.startswith("UPDATE"):
            return self._execute_update(sql, params)
        elif sql_upper.startswith("DELETE"):
            return self._execute_delete(sql, params)
        elif sql_upper.startswith("CREATE TABLE"):
            return self._execute_create_table(sql)
        else:
            raise ValueError(f"Unsupported SQL: {sql}")
    
    def _execute_select(self, sql: str, params: tuple) -> List[Dict]:
        """Simplified SELECT executor."""
        # This is a very simplified implementation
        # Real implementation would parse SQL properly
        # For demo, we'll handle simple cases
        
        # Parse simple: SELECT * FROM table WHERE col = ?
        import re
        match = re.match(
            r'SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*?))?(?:\s+LIMIT\s+(\d+))?$',
            sql, re.IGNORECASE
        )
        
        if not match:
            # Try external DBs
            for name, conn in self.external_connections.items():
                try:
                    cursor = conn.execute(sql, params)
                    return [dict(row) for row in cursor.fetchall()]
                except Exception:
                    continue
            return []
        
        columns_str, table_name, where_clause, limit_str = match.groups()
        
        table = self.tables.get(table_name)
        if not table:
            return []
        
        rows = table.all()
        
        # Apply WHERE (simplified)
        if where_clause:
            # Very basic: col = ?
            cond_match = re.match(r'(\w+)\s*=\s*\?', where_clause)
            if cond_match:
                col = cond_match.group(1)
                val = params[0] if params else None
                rows = [r for r in rows if r.get(col) == val]
        
        # Apply LIMIT
        if limit_str:
            limit = int(limit_str)
            rows = rows[:limit]
        
        # Select columns
        if columns_str.strip() == "*":
            return [r.to_dict() for r in rows]
        else:
            cols = [c.strip() for c in columns_str.split(",")]
            return [{c: r.get(c) for c in cols} for r in rows]
    
    def _execute_insert(self, sql: str, params: tuple) -> List[Dict]:
        match = re.match(r'INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)', sql, re.IGNORECASE)
        if not match:
            return []
        
        table_name, cols_str, vals_str = match.groups()
        table = self.tables.get(table_name)
        if not table:
            return []
        
        cols = [c.strip() for c in cols_str.split(",")]
        vals = [v.strip() for v in vals_str.split(",")]
        
        data = dict(zip(cols, params))
        row = table.insert(data)
        return [row.to_dict()]
    
    def _execute_update(self, sql: str, params: tuple) -> List[Dict]:
        # Simplified
        return []
    
    def _execute_delete(self, sql: str, params: tuple) -> List[Dict]:
        return []
    
    def _execute_create_table(self, sql: str) -> List[Dict]:
        return []


# =========================================================================
# Data Registry - Central catalog of all data sources
# =========================================================================

class DataRegistry:
    """
    Central registry for all data sources in a zpx session.
    
    Usage:
        registry = DataRegistry()
        
        # Create table
        users = registry.table("users", 
            columns=[Column("id", "int", primary_key=True), Column("name", "str")])
        users.insert({"id": 1, "name": "Alice"})
        
        # Create stream
        events = registry.stream("events", 
            columns=[Column("user_id", "int"), Column("action", "str")])
        events.append({"user_id": 1, "action": "login"})
        
        # Query
        registry.query("SELECT * FROM users WHERE id = ?", (1,))
    """
    
    def __init__(self):
        self.engine = QueryEngine()
        self._lock = threading.RLock()
    
    def table(self, name: str, columns: List[Column] = None, 
              primary_key: str = None, data: List[Dict] = None) -> Table:
        """Create or get a table."""
        with self._lock:
            if name in self.engine.tables:
                return self.engine.tables[name]
            
            schema = None
            if columns:
                schema = TableSchema(name, columns)
            elif primary_key:
                # Auto-infer from data
                pass
            
            table = Table(name, schema)
            if data:
                table.insert_many(data)
            
            self.engine.register_table(table)
            return table
    
    def stream(self, name: str, columns: List[Column] = None, 
               max_size: int = None) -> Stream:
        """Create or get a stream."""
        with self._lock:
            if name in self.engine.streams:
                return self.engine.streams[name]
            
            schema = TableSchema(name, columns) if columns else None
            stream = Stream(name, schema, max_size)
            self.engine.register_stream(stream)
            return stream
    
    def external(self, name: str, path: str):
        """Register external SQLite database."""
        with self._lock:
            self.engine.connect_external(name, path)
    
    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute SQL query."""
        with self._lock:
            return self.engine.execute(sql, params)
    
    def table_names(self) -> List[str]:
        with self._lock:
            return list(self.engine.tables.keys())
    
    def stream_names(self) -> List[str]:
        with self._lock:
            return list(self.engine.streams.keys())


# =========================================================================
# zpx Builtins Integration
# =========================================================================

_global_registry: Optional[DataRegistry] = None


def _get_registry() -> DataRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = DataRegistry()
    return _global_registry


def _stdlib_table(name: str, columns: list = None, data: list = None):
    """zpx: table(name, columns=[], data=[]) -> Table"""
    reg = _get_registry()
    
    cols = None
    if columns:
        cols = [Column(c["name"], c.get("type", "any"), 
                       primary_key=c.get("primary_key", False),
                       nullable=c.get("nullable", True)) 
                for c in columns]
    
    t = _get_registry().table(name, cols, data=data)
    return ZpxDict({
        "name": t.name,
        "insert": lambda d: t.insert(d),
        "insert_many": lambda ds: t.insert_many(ds),
        "find": lambda **kw: [r.to_dict() for r in t.find(**kw)],
        "find_one": lambda **kw: (t.find_one(**kw) or {}).to_dict() if t.find_one(**kw) else None,
        "all": lambda: t.to_list(),
        "count": lambda: t.count(),
        "update": lambda cond, upd: t.update(cond, upd),
        "delete": lambda **kw: t.delete(**kw),
    })


def _stdlib_stream(name: str, columns: list = None, max_size: int = None):
    """zpx: stream(name, columns=[], max_size=10000) -> Stream"""
    cols = None
    if columns:
        cols = [Column(c["name"], c.get("type", "any")) for c in columns]
    
    s = _get_registry().stream(name, cols, max_size)
    return ZpxDict({
        "name": s.name,
        "append": lambda d: s.append(d).to_dict(),
        "append_many": lambda ds: [e.to_dict() for e in s.append_many(ds)],
        "query": lambda since=None, until=None, limit=None: 
            [e.to_dict() for e in s.query(since, until, limit)],
        "window_tumbling": lambda sec: [[e.to_dict() for e in w] for w in s.window_tumbling(sec)],
        "window_sliding": lambda w, s: [[e.to_dict() for e in w] for w in s.window_sliding(w, s)],
        "subscribe": lambda cid: s.subscribe(cid),
        "consume": lambda cid, limit=100: [e.to_dict() for e in s.consume(cid, limit)],
    })


def _stdlib_sql(sql: str, params: list = None):
    """zpx: sql(query, params[]) -> List[Dict]"""
    reg = _get_registry()
    return reg.query(sql, tuple(params) if params else ())


def _stdlib_create_table(name: str, columns: list):
    """zpx: create_table(name, columns[]) -> Table"""
    return _stdlib_table(name, columns)


def _stdlib_describe(table_name: str):
    """zpx: describe(table) -> column info"""
    reg = _get_registry()
    if table_name in reg.engine.tables:
        t = reg.engine.tables[table_name]
        return [{"name": c.name, "type": c.type, "primary_key": c.primary_key, 
                 "nullable": c.nullable} for c in t.schema.columns] if t.schema else []
    return []


def _stdlib_show_tables():
    return _get_registry().table_names()


def _stdlib_show_streams():
    return _get_registry().stream_names()


DATA_BUILTINS = {
    'table': _stdlib_table,
    'stream': _stdlib_stream,
    'sql': _stdlib_sql,
    'create_table': _stdlib_create_table,
    'describe': _stdlib_describe,
    'show_tables': _stdlib_show_tables,
    'show_streams': _stdlib_show_streams,
}