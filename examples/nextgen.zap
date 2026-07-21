# ===== PERSISTENT SEMANTIC MEMORY =====
# store project context that AI tools can read
context_set("project.name", "Zap NextGen")
context_set("project.version", "0.2")
context_set("author", "AI Collaboration")

context_add_convention("functions should be pure when possible")
context_add_decision("use tensor @@ for matrix multiply")

say("context saved:", context_get("project.name"))

# ===== INTENT-ORIENTED PROGRAMMING =====
# just say what you want - intent is stored for AI tools
intend "build a customer dashboard with auth and analytics"
intend "add self-healing capabilities to all API endpoints"

say("intents recorded:", len(context_intents()))

# ===== CONTRACT ANNOTATIONS =====
# @requires checks inputs, @ensures checks outputs

fn divide(a, b):
  a / b

say("5 / 2 =", divide(5, 2))

@requires(b != 0)
@ensures(result > 0)
fn safe_divide(a, b):
  a / b

say("safe_divide:", safe_divide(10, 2))

# ===== SELF-HEALING =====
# @retry automatically retries on failure

let attempt = 0

@retry(10, 0.01)
fn flaky_api():
  attempt = attempt + 1
  let x = random()
  say("  attempt", attempt, "x =", round(x, 3))
  if x < 0.5:
    1 / 0
  "success after " + str(attempt) + " attempts"

say("flaky result:", flaky_api())

# ===== DISTRIBUTED EXECUTION =====
# pmap runs a function over items in parallel

fn slow_square(n):
  wait(0.05)
  n * n

let nums = [1, 2, 3, 5, 8]
let squares = pmap(slow_square, nums)
say("parallel squares:", squares)

# parallel runs multiple functions concurrently
fn task_a():
  wait(0.05)
  "done1"

fn task_b():
  wait(0.05)
  "done2"

let results = parallel(task_a, task_b)
say("parallel results:", results)

say("--- all next-gen features working ---")
