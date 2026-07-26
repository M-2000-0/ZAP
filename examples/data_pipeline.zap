# Data Processing Pipeline — Zap makes data transforms easy

# Sample data: sales transactions
let transactions = [
  {product: "Laptop", amount: 999, category: "Electronics", quantity: 1},
  {product: "Mouse", amount: 25, category: "Electronics", quantity: 3},
  {product: "Desk", amount: 150, category: "Furniture", quantity: 1},
  {product: "Chair", amount: 200, category: "Furniture", quantity: 2},
  {product: "Keyboard", amount: 75, category: "Electronics", quantity: 2},
  {product: "Monitor", amount: 350, category: "Electronics", quantity: 1},
  {product: "Lamp", amount: 45, category: "Furniture", quantity: 4},
]

# Helper functions
fn total(t):
  ret t["amount"] * t["quantity"]

fn format_currency(amount):
  ret "$" + str(amount)

# Pipeline: Calculate total revenue
let revenues = [total(t) for t in transactions]
let total_revenue = 0
for r in revenues:
  total_revenue = total_revenue + r

print("=== Sales Analytics ===")
print("")
print("Total Revenue: " + format_currency(total_revenue))
print("Transactions: " + str(len(transactions)))
print("")

# Group by category
let electronics = [t for t in transactions if t["category"] == "Electronics"]
let furniture = [t for t in transactions if t["category"] == "Furniture"]

let electronics_total = 0
for t in electronics:
  electronics_total = electronics_total + total(t)

let furniture_total = 0
for t in furniture:
  furniture_total = furniture_total + total(t)

print("Revenue by Category:")
print("  Electronics: " + format_currency(electronics_total))
print("  Furniture: " + format_currency(furniture_total))
print("")

# Top products by revenue
let product_revenues = {t["product"]: total(t) for t in transactions}
print("Revenue by Product:")
for product in product_revenues:
  print("  " + product + ": " + format_currency(product_revenues[product]))
print("")

# Average order value
let avg_order = total_revenue / len(transactions)
print("Average Order Value: " + format_currency(avg_order))

# High-value transactions
let high_value = [t for t in transactions if total(t) > 200]
print("")
print("High-Value Transactions (>$200):")
for t in high_value:
  print("  " + t["product"] + ": " + format_currency(total(t)))
