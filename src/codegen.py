import os
import re
from .ast_nodes import *

TEMPLATES = {}

TEMPLATES['service'] = '''\
service {name}:
{expose}
{methods}
'''

TEMPLATES['schema'] = '''\
schema {name}:
{fields}
'''

TEMPLATES['model'] = '''\
model {name}:
{fields}
{methods}
'''

TEMPLATES['api'] = '''\
api {method} "{path}"{returns}:
  fn handle({params}):
    {body}
'''

TEMPLATES['page'] = '''\
page {name} "{route}":
  {body}
'''

TEMPLATES['database'] = '''\
database {name}:
{tables}
'''


# ---- Individual generators ----

def generate_service(name, endpoints=None):
    if endpoints is None:
        endpoints = []
    expose_lines = '\n'.join(f'  expose {e}' for e in endpoints)
    method_lines = []
    for ep in endpoints:
        method_lines.append(f'''\
  fn {ep}(req):
    ret {{"status": "ok", "endpoint": "{ep}"}}''')
    methods = '\n'.join(method_lines)
    return TEMPLATES['service'].format(
        name=name, expose=expose_lines, methods=methods
    )


def generate_schema(name, fields=None):
    if fields is None:
        fields = [('id', 'int'), ('name', 'str'), ('created_at', 'str')]
    field_lines = '\n'.join(f'  {n}: {t}' for n, t in fields)
    return TEMPLATES['schema'].format(name=name, fields=field_lines)


def generate_model(name, fields=None, methods_desc=None):
    if fields is None:
        fields = [('id', 'int'), ('name', 'str')]
    if methods_desc is None:
        methods_desc = []
    field_lines = '\n'.join(f'  {n}: {t}' for n, t in fields)
    method_lines = []
    for m in methods_desc:
        if isinstance(m, str):
            method_lines.append(f'  fn {m}():')
            method_lines.append(f'    ret none')
        else:
            method_lines.append(f'  fn {m["name"]}({", ".join(m.get("params", []))}):')
            method_lines.append(f'    {m.get("body", "ret none")}')
    methods = '\n'.join(method_lines)
    return TEMPLATES['model'].format(
        name=name, fields=field_lines, methods=methods
    )


def generate_api(method='GET', path='/', handler_body='ret {"ok": true}', params=None, returns=None):
    returns_str = f' -> {returns}' if returns else ''
    params_str = ', '.join(params) if params else 'req'
    body = handler_body.replace('\n', '\n    ')
    return TEMPLATES['api'].format(
        method=method, path=path, returns=returns_str,
        params=params_str, body=body,
    )


def generate_page(name, route='/', components_desc=None):
    if components_desc is None:
        components_desc = [f"say('hello from {name}')"]
    body = '\n  '.join(components_desc)
    return TEMPLATES['page'].format(name=name, route=route, body=body)


def generate_database(name, tables=None):
    if tables is None:
        tables = []
    table_lines = []
    for t in tables:
        if isinstance(t, str):
            table_lines.append(generate_schema(t))
        elif isinstance(t, tuple):
            table_lines.append(generate_schema(t[0], t[1]))
        else:
            table_lines.append(generate_schema(t.get('name'), t.get('fields')))
    tables_str = '\n'.join('  ' + l if l.strip() else l for l in '\n'.join(table_lines).split('\n'))
    result = TEMPLATES['database'].format(name=name, tables=tables_str)
    if not result.endswith('\n'):
        result += '\n'
    return result


# ---- CRUD generator for a single entity ----

def generate_crud(entity_name, fields=None):
    """Generate all layers for one entity."""
    if fields is None:
        fields = [('id', 'int'), ('name', 'str')]

    schema = generate_schema(entity_name, fields)
    model = generate_model(entity_name, fields, methods_desc=[
        {'name': 'validate', 'params': ['self'],
         'body': 'ret True'},
    ])

    service = generate_service(f'{entity_name}Service', [
        f'create_{entity_name.lower()}',
        f'get_{entity_name.lower()}',
        f'list_{entity_name.lower()}',
        f'update_{entity_name.lower()}',
        f'delete_{entity_name.lower()}',
    ])

    api_list = []
    api_list.append(generate_api(
        'GET', f'/{entity_name.lower()}s',
        f'ret {entity_name}Service.list_{entity_name.lower()}(req)',
        returns='list'
    ))
    api_list.append(generate_api(
        'GET', f'/{entity_name.lower()}s/{{id}}',
        f'ret {entity_name}Service.get_{entity_name.lower()}(req)',
        returns=entity_name
    ))
    api_list.append(generate_api(
        'POST', f'/{entity_name.lower()}s',
        f'ret {entity_name}Service.create_{entity_name.lower()}(req)',
        returns=entity_name
    ))
    api_list.append(generate_api(
        'PUT', f'/{entity_name.lower()}s/{{id}}',
        f'ret {entity_name}Service.update_{entity_name.lower()}(req)',
        returns=entity_name
    ))
    api_list.append(generate_api(
        'DELETE', f'/{entity_name.lower()}s/{{id}}',
        f'ret {entity_name}Service.delete_{entity_name.lower()}(req)',
        returns='status'
    ))

    page = generate_page(
        f'{entity_name}List',
        f'/{entity_name.lower()}s',
        [f"say('{entity_name} CRUD generated')",
         f"say('endpoints: /{entity_name.lower()}s [GET, POST, PUT, DELETE]')"]
    )

    return {
        'schema': schema,
        'model': model,
        'service': service,
        'apis': api_list,
        'page': page,
        'name': entity_name,
        'singular': entity_name.lower(),
        'plural': entity_name.lower() + 's',
    }


# ---- App generator ----

def generate_app(entities):
    """Generate a full multi-entity app from entity descriptions."""
    from .lexer import Lexer
    from .parser import Parser

    lines = ['# Auto-generated by zap codegen']
    lines.append('')

    # Schema + Model for each entity
    for ent in entities:
        name = ent.get('name', 'Entity')
        fields = ent.get('fields', [('id', 'int'), ('name', 'str')])
        lines.append(generate_schema(name, fields))
        lines.append(generate_model(name, fields, methods_desc=[
            {'name': 'validate', 'params': ['self'],
             'body': 'ret True'},
        ]))
        lines.append('')

    # Database
    db_tables = [(e['name'], e.get('fields', [('id', 'int'), ('name', 'str')])) for e in entities]
    lines.append(generate_database('AppDB', db_tables))
    lines.append('')

    # Services
    for ent in entities:
        name = ent['name']
        lines.append(generate_service(f'{name}Service', [
            f'create_{name.lower()}',
            f'get_{name.lower()}',
            f'list_{name.lower()}',
            f'update_{name.lower()}',
            f'delete_{name.lower()}',
        ]))
        lines.append('')

    # APIs
    for ent in entities:
        name = ent['name']
        sn = name.lower()
        lines.append(generate_api('GET', f'/{sn}s',
            f'ret {name}Service.list_{sn}(req)', returns='list'))
        lines.append(generate_api('GET', f'/{sn}s/{{id}}',
            f'ret {name}Service.get_{sn}(req)', returns=name))
        lines.append(generate_api('POST', f'/{sn}s',
            f'ret {name}Service.create_{sn}(req)', returns=name))
        lines.append(generate_api('PUT', f'/{sn}s/{{id}}',
            f'ret {name}Service.update_{sn}(req)', returns=name))
        lines.append(generate_api('DELETE', f'/{sn}s/{{id}}',
            f'ret {name}Service.delete_{sn}(req)', returns='status'))
        lines.append('')

    # Pages
    for ent in entities:
        name = ent['name']
        sn = name.lower()
        lines.append(generate_page(f'{name}Page', f'/{sn}s', [
            f"say('{name} management')",
            f"say('use /{sn}s endpoints for CRUD')",
        ]))
        lines.append('')

    # Verify
    source = '\n'.join(lines)
    result = validate_generated(source)
    if not result['valid']:
        source = f'# WARNING: generated code may have errors\n{source}'
    return source


# ---- Keyword-based scaffold ----

RELATION_PATTERNS = [
    (r'\bhas many\b', 'has_many'),
    (r'\bbelongs to\b', 'belongs_to'),
    (r'\bhas one\b', 'has_one'),
    (r'\bmany to many\b', 'many_to_many'),
]

ENTITY_EXTRACTOR = re.compile(r'\b([A-Z]\w*)\b')


def parse_description(desc):
    """Extract entities and relationships from a natural-language description."""
    desc_lower = desc.lower()
    entities = []

    # Look for patterns like "a todo app with users and tasks"
    entity_matches = ENTITY_EXTRACTOR.findall(desc)
    known_entities = set()
    for em in entity_matches:
        lower = em.lower()
        if lower not in ('App', 'I', 'The', 'A', 'An', 'This', 'That', 'It', 'We', 'You', 'They',
                         'Crud', 'Api', 'Ui', 'Db', 'Id', 'All', 'Each', 'Every', 'Some', 'Many',
                         'Several', 'Both', 'No', 'None', 'One', 'Two', 'Three', 'Four', 'Five'):
            known_entities.add(em)

    # Default fields based on common domain patterns
    default_fields_map = {
        'user': [('id', 'int'), ('name', 'str'), ('email', 'str'), ('role', 'str')],
        'task': [('id', 'int'), ('title', 'str'), ('description', 'str'), ('status', 'str'), ('assignee_id', 'int')],
        'product': [('id', 'int'), ('name', 'str'), ('price', 'float'), ('description', 'str')],
        'order': [('id', 'int'), ('user_id', 'int'), ('total', 'float'), ('status', 'str')],
        'customer': [('id', 'int'), ('name', 'str'), ('email', 'str'), ('phone', 'str')],
        'post': [('id', 'int'), ('title', 'str'), ('content', 'str'), ('author_id', 'int')],
        'comment': [('id', 'int'), ('post_id', 'int'), ('author', 'str'), ('content', 'str')],
        'project': [('id', 'int'), ('name', 'str'), ('description', 'str'), ('owner_id', 'int')],
        'tag': [('id', 'int'), ('name', 'str')],
        'category': [('id', 'int'), ('name', 'str'), ('description', 'str')],
    }

    for ent_name in known_entities:
        lower = ent_name.lower()
        name = ent_name[0].upper() + ent_name[1:] if len(ent_name) > 1 else ent_name.upper()
        fields = default_fields_map.get(lower, [('id', 'int'), ('name', 'str'), ('created_at', 'str')])
        entities.append({'name': name, 'fields': fields})

    # If no entities found, use defaults
    if not entities:
        default_entities = ['User', 'Task'] if 'task' in desc_lower or 'todo' in desc_lower else ['User']
        for de in default_entities:
            fields = default_fields_map.get(de.lower(), [('id', 'int'), ('name', 'str')])
            entities.append({'name': de, 'fields': fields})

    return entities


def scaffold(description):
    """Generate a full app from a natural-language description."""
    entities = parse_description(description)
    return generate_app(entities)


# ---- Validation ----

def validate_generated(source, filename='<generated>'):
    from .lexer import Lexer
    from .parser import Parser
    from .evaluator import Evaluator
    try:
        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        ev = Evaluator(is_main=False)
        ev.evaluate(ast)
        return {'valid': True, 'errors': []}
    except (SyntaxError, NameError, RuntimeError, ZeroDivisionError, TypeError, ValueError) as e:
        return {'valid': False, 'errors': [str(e)]}
