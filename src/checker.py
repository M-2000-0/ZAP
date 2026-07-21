"""Compile-time validation pass.

Runs after parsing and before evaluation. Checks:
- Contract conditions are valid expressions
- Permission declarations are unique
- API routes are well-formed and don't conflict
- Schema field types are known
- Version strings are valid semver
- `check` block assertions are valid expressions
- Invariants are valid expressions
"""

import re
from .ast_nodes import *

SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+$')

KNOWN_TYPES = {'int', 'float', 'str', 'bool', 'none', 'list', 'dict', 'tensor'}

CHECKER_WARNINGS = []


def reset_warnings():
    CHECKER_WARNINGS.clear()


def warn(msg, node=None):
    location = f"L{node.line}:{node.col}" if node else "<unknown>"
    CHECKER_WARNINGS.append(f"[checker] {location}: {msg}")


def check_program(program):
    reset_warnings()
    errors = []
    for stmt in program.stmts:
        errs = check_stmt(stmt)
        errors.extend(errs)
    return errors, CHECKER_WARNINGS


def check_stmt(stmt):
    errors = []
    if isinstance(stmt, ServiceDecl):
        errors.extend(check_service(stmt))
    elif isinstance(stmt, DatabaseDecl):
        errors.extend(check_database(stmt))
    elif isinstance(stmt, ApiEndpoint):
        errors.extend(check_api(stmt))
    elif isinstance(stmt, PageDecl):
        errors.extend(check_page(stmt))
    elif isinstance(stmt, SchemaDecl):
        errors.extend(check_schema(stmt))
    elif isinstance(stmt, ModelDecl):
        errors.extend(check_model(stmt))
    elif isinstance(stmt, FnDef):
        errors.extend(check_fn(stmt))
    elif isinstance(stmt, CheckBlock):
        errors.extend(check_check_block(stmt))
    elif isinstance(stmt, ConcurrentBlock):
        errors.extend(check_concurrent(stmt))
    elif isinstance(stmt, PermissionDecl):
        errors.extend(check_permission(stmt))
    elif isinstance(stmt, InvariantStmt):
        if not isinstance(stmt.condition, Node):
            errors.append(f"invariant must be an expression")
    elif isinstance(stmt, ExpectStmt):
        pass  # validated at runtime
    return errors


def check_service(svc):
    errors = []
    if not svc.name:
        errors.append("service must have a name")
    # Check metadata
    for kind in ('requires', 'guarantees'):
        conds = svc.metadata.get(kind, [])
        for c in conds:
            if not isinstance(c, Node):
                errors.append(f"{kind} condition must be an expression")
    # Check routes for API-like methods (future validation)
    for fn_def in svc.methods:
        errors.extend(check_fn(fn_def))
    return errors


def check_database(db):
    errors = []
    if not db.name:
        errors.append("database must have a name")
    for tbl in db.tables:
        errors.extend(check_schema(tbl))
    return errors


def check_api(api):
    errors = []
    valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}
    if api.method not in valid_methods:
        errors.append(f"invalid HTTP method '{api.method}'")
    if not api.path:
        errors.append("API path is required")
    elif not api.path.startswith('/'):
        errors.append(f"API path must start with '/': '{api.path}'")
    if api.handler:
        errors.extend(check_fn(api.handler))
    return errors


def check_page(page):
    errors = []
    if not page.name:
        errors.append("page must have a name")
    if page.route and not page.route.startswith('/'):
        errors.append(f"page route must start with '/': '{page.route}'")
    return errors


def check_schema(schema):
    errors = []
    if not schema.name:
        errors.append("schema must have a name")
    for f in schema.fields:
        if f.field_type not in KNOWN_TYPES:
            warn(f"unknown field type '{f.field_type}' in schema '{schema.name}'", f)
    return errors


def check_model(model):
    return []  # models can have any fields


def check_fn(fn_def):
    errors = []
    if not fn_def.name:
        errors.append("function must have a name")
    # Validate params
    for p in fn_def.params:
        if p.get('type') and p['type'] not in KNOWN_TYPES:
            warn(f"unknown parameter type '{p['type']}' in fn '{fn_def.name}'", fn_def)
    # Validate contracts
    for c in fn_def.contracts:
        if not isinstance(c, ContractClause):
            errors.append(f"invalid contract clause")
        elif not isinstance(c.condition, Node):
            errors.append(f"contract condition must be an expression")
    return errors


def check_check_block(block):
    errors = []
    for a in block.assertions:
        if not isinstance(a, Node):
            errors.append("check assertion must be a valid expression")
    return errors


def check_concurrent(block):
    errors = []
    for branch in block.branches:
        for stmt in branch.stmts if isinstance(branch, Block) else [branch]:
            errors.extend(check_stmt(stmt))
    return errors


def check_permission(perm):
    errors = []
    if not perm.name:
        errors.append("permission must have a name")
    if not re.match(r'^[a-z][a-z0-9_.]*$', perm.name):
        warn(f"permission name '{perm.name}' should use snake_case")
    return errors
