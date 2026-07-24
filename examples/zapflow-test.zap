# ── ZapFlow End-to-End Test ──
# This file tests: DAG execution, node types, API calls, data pipelines

import "workflow_engine.zap" as engine

fn test_basic_workflow()
  print("[Test] Creating basic workflow...")

  let wf = engine.create_workflow("Basic Workflow Test")

  # Create nodes
  let n1 = engine.add_node(wf, "trigger", {})
  let n2 = engine.add_node(wf, "http_request", {
    method: "GET",
    url: "https://jsonplaceholder.typicode.com/todos/1"
  })
  let n3 = engine.add_node(wf, "filter", {
    field: "completed",
    operator: "equals",
    value: false
  })
  let n4 = engine.add_node(wf, "transform", {expression: "uppercase"})

  # Connect nodes
  engine.add_edge(wf, n1.id, n2.id, "data")
  engine.add_edge(wf, n2.id, n3.id, "data")
  engine.add_edge(wf, n3.id, n4.id, "data")

  # Save workflow
  let saved = engine.save_workflow(wf)
  print("[Test] Workflow saved with ID: " + wf.id)

  # Execute workflow
  let result = engine.execute_workflow(wf, {
    trigger_source: "manual",
    user_data: {}
  })

  print("[Test] Workflow executed")
  let result_str = ""
  for key in keys(result):
    let item = result[key]
    if item and len(item) > 0:
      result_str = result_str + "  " + key + ": " + str(item) + "\n"
  print("[Test] Result preview:\n" + result_str)

  ret result

fn test_advanced_pipeline()
  print("[Test] Creating advanced pipeline...")

  let wf = engine.create_workflow("Advanced Data Pipeline")

  # Create nodes
  let start = engine.add_node(wf, "webhook", {path: "/process-data"})
  let extract = engine.add_node(wf, "database", {
    action: "query",
    table: "data_table",
    query: "SELECT * FROM data_table WHERE status = 'pending'"
  })
  let transform1 = engine.add_node(wf, "transform", {expression: "uppercase"})
  let filter1 = engine.add_node(wf, "filter", {
    field: "id",
    operator: "gt",
    value: 100
  })
  let delay = engine.add_node(wf, "delay", {seconds: 2})
  let transform2 = engine.add_node(wf, "code", {language: "javascript", source: "return x * 2"})
  let notify = engine.add_node(wf, "notification", {message: "Pipeline completed"})

  # Connect DAG
  engine.add_edge(wf, start.id, extract.id, "data")
  engine.add_edge(wf, extract.id, transform1.id, "data")
  engine.add_edge(wf, transform1.id, filter1.id, "data")
  engine.add_edge(wf, filter1.id, delay.id, "data")
  engine.add_edge(wf, delay.id, transform2.id, "data")
  engine.add_edge(wf, transform2.id, notify.id, "data")

  # Save and execute
  engine.save_workflow(wf)

  let sample_data = [
    {id: 50, status: "pending", value: "test"},
    {id: 200, status: "pending", value: "another"},
    {id: 150, status: "pending", value: "third"}
  ]

  let result = engine.execute_workflow(wf, {
    source: "test",
    trigger_data: {
      data: sample_data
    }
  })

  print("[Test] Advanced pipeline result preview:")
  let result_str = ""
  for key in keys(result):
    let item = result[key]
    if item:
      result_str = result_str + "  " + key + ": " + str(item) + "\n"
  print(result_str)

  ret result

fn test_webhook_trigger()
  print("[Test] Testing webhook integration...")

  let wf = engine.create_workflow("Webhook Listener")

  # Create webhook node
  let webhook_node = engine.add_node(wf, "webhook", {
    method: "POST",
    path: "/api/webhook/test",
    headers: {"Content-Type": "application/json"}
  })

  # Create processing nodes
  let process_node = engine.add_node(wf, "transform", {expression: "uppercase"})
  let store_node = engine.add_node(wf, "database", {
    action: "insert",
    table: "events",
    query: "INSERT INTO events (event_id, event_data, status) VALUES (?, ?, ?)"
  })

  # Connect nodes
  engine.add_edge(wf, webhook_node.id, process_node.id, "data")
  engine.add_edge(wf, process_node.id, store_node.id, "data")

  engine.save_workflow(wf)

  # Simulate webhook payload
  let payload = {
    event: "user.created",
    data: {id: 123, email: "test@example.com"}
  }

  let result = engine.execute_workflow(wf, {
    source: "webhook",
    webhook_path: "/api/webhook/test",
    body: payload
  })

  print("[Test] Webhook workflow result:")
  ret result

fn test_api_automatic_creation()
  print("[Test] Testing automatic API route creation...")

  # Test that ZapFlow API server automatically creates routes
  print("[Test] API server would create the following routes:")
  print("  GET    /              (Dashboard)")
  print("  GET    /new           (New workflow form)")

  # Get workflow list (would be served by API)
  let workflows_str = engine.api_list()

  print("[Test] Workflows API response:")
  print(workflows_str)

  ret "API ready"

fn main_test()
  print("")
  print("  ⚡ ZapFlow v0.1 — End-to-End Test Suite")
  print("")

  let test1 = test_basic_workflow()
  print("")

  let test2 = test_advanced_pipeline()
  print("")

  let test3 = test_webhook_trigger()
  print("")

  let test4 = test_api_automatic_creation()
  print("")

  print("  ✅ All tests completed!")
  print("")

main_test()
