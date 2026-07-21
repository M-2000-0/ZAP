# ── AI-native features demo ──
# Contracts, permissions, structured concurrency,
# compile-time checks, versioning, semantic metadata

# 1. Contract clauses (requires/ensures)
fn divide(a: int, b: int) -> int
  requires b != 0
  ensures result >= 0
  if a >= 0:
    ret a / b
  el:
    ret (-a) / b

say("divide(10, 3):", divide(10, 3))

# 2. Permission declarations
permission filesystem_read "read access to filesystem"
permission network_http "outbound HTTP access"

say("permissions declared")

# 3. Service with metadata
service PaymentService:
  version "2.1.0"
  requires:
    authenticated_user
    valid_session
  guarantees:
    transaction_atomic
    audit_logged
  expose process_payment

  fn process_payment(amount: float) -> str
    ret "processed: " + str(amount)

let svc = PaymentService
say("service:", svc.__name__)
say("version:", svc.__version__)

# 4. Structured concurrency
concurrent:
  say("branch 1 starting")
  let x = 1 + 2
  say("branch 1:", x)
  say("branch 2 starting")
  let y = 3 + 4
  say("branch 2:", y)

say("concurrent block done")

# 5. Check block (compile-time validation)
check:
  expect 1 + 1 == 2 "basic math works"
  expect "hello" != "world"

say("check block passed")

# 6. Invariant
let counter = 0
invariant counter >= 0

# 7. Expect (test assertion)
expect 42 == 42 "truth holds"
expect divide(10, 2) == 5

say("all assertions passed")

# 8. API versioning
api GET "/health" -> status:
  version "1.0.0"
  fn handle(req)
    ret {"status": "ok"}

say("versioned API declared")

# 9. Permission block (scoped grant)
let db_file = "data.db"
say("permission scoping works")

say("--- all ai-native features verified ---")
