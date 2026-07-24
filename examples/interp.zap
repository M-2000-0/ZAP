# Test string interpolation
let name = "Zap"
let v = 42

# Simple $var syntax
print("Hello $name!")

# ${expr} syntax
print("Version: ${v * 2}")

# Mixed
let lang = "AI"
print("$name is great for $lang")
print("${name} v${v}")
