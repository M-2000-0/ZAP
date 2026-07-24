# db.zap — High-level database library with auto-deploy support

# Auto-detect database URL from deployment platform
let DEFAULT_DB = env("DATABASE_URL") or env("DATABASE_PATH") or "sqlite://./app.db"
let _db_name = "default"

db_open(_db_name, DEFAULT_DB)

# --- Schema definition helpers ---

fn define_table(name, fields):
    let sql = "CREATE TABLE IF NOT EXISTS " + name + " ("
    let first = true
    for field_name in fields:
        let field_type = fields[field_name]
        if not first:
            sql = sql + ", "
        sql = sql + field_name + " " + field_type
        first = false
    sql = sql + ")"
    db_exec(_db_name, sql)

fn db_auto_open(name, schema):
    db_open(name)
    for table_name in schema:
        define_table(table_name, schema[table_name])
    ret name

fn db_close_connect(name):
    db_close(name)

# --- Query helpers ---

fn db_row(sql, params=none):
    ret db_query_one(_db_name, sql, params)

fn db_rows(sql, params=none):
    ret db_query(_db_name, sql, params)

fn db_insert(table, data):
    let keys = []
    let vals = []
    let placeholders = []
    let i = 0
    for k in data:
        keys.append(k)
        vals.append(data[k])
        placeholders.append("?" + str(i))
        i = i + 1
    let sql = "INSERT INTO " + table + " (" + keys.join(", ") + ") VALUES (" + placeholders.join(", ") + ")"
    db_exec(_db_name, sql, vals)
    ret db_query_one(_db_name, "SELECT last_insert_rowid() as id")

fn db_update(table, data, where="1=1", params=none):
    let set_parts = []
    let all_params = []
    for k in data:
        set_parts.append(k + " = ?")
        all_params.append(data[k])
    let sql = "UPDATE " + table + " SET " + set_parts.join(", ") + " WHERE " + where
    if params != none:
        all_params = all_params + params
    db_exec(_db_name, sql, all_params)

fn db_delete(table, where="1=1", params=none):
    let sql = "DELETE FROM " + table + " WHERE " + where
    db_exec(_db_name, sql, params)

fn db_select(table, columns="*", where="1=1", params=none):
    let sql = "SELECT " + columns + " FROM " + table + " WHERE " + where
    ret db_query(_db_name, sql, params)

fn db_exists(table, id):
    let row = db_row("SELECT id FROM " + table + " WHERE id = ?", [id])
    ret row != none

fn db_count(table, where="1=1", params=none):
    let row = db_row("SELECT COUNT(*) as cnt FROM " + table + " WHERE " + where, params)
    ret row["cnt"] if row != none else 0

# --- JSON REST helper ---

fn db_to_json(rows):
    let parts = []
    for row in rows:
        parts.append(str(row))
    ret "[" + parts.join(", ") + "]"

# --- Deployment platform detection ---

fn db_platform():
    if env("VERCEL") == "1":
        ret "vercel"
    if env("NETLIFY") == "true":
        ret "netlify"
    if env("RENDER") != none:
        ret "render"
    if env("FLY_REGION") != none:
        ret "fly"
    if env("DYNO") != none:
        ret "heroku"
    if env("REPL_ID") != none:
        ret "replit"
    ret "self_hosted"

# --- Migration helper ---

fn db_migrate_version(name, version):
    db_migrate(_db_name, name + "_" + str(version))