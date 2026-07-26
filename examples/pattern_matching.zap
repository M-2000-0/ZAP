# Pattern Matching and Algebraic Data Types

# Define a shape type
fn area(shape):
  match shape["type"]:
    "circle":
      ret 3.14159 * shape["radius"] * shape["radius"]
    "rectangle":
      ret shape["width"] * shape["height"]
    "triangle":
      ret 0.5 * shape["base"] * shape["height"]
  el:
    ret 0

fn describe(shape):
  match shape["type"]:
    "circle":
      ret "Circle with radius " + str(shape["radius"])
    "rectangle":
      ret "Rectangle " + str(shape["width"]) + "x" + str(shape["height"])
    "triangle":
      ret "Triangle with base " + str(shape["base"]) + " and height " + str(shape["height"])
  el:
    ret "Unknown shape"

# Create shapes
let shapes = [
  {type: "circle", radius: 5},
  {type: "rectangle", width: 10, height: 4},
  {type: "triangle", base: 8, height: 6},
]

# Calculate areas
print("=== Shape Calculator ===")
print("")

for s in shapes:
  print(describe(s))
  print("  Area: " + str(area(s)))
  print("")

# Total area
let total_area = 0
for s in shapes:
  total_area = total_area + area(s)
print("Total Area: " + str(total_area))

# Pattern matching with complex conditions
fn classify_number(n):
  if n == 0:
    ret "zero"
  if n > 0:
    if n % 2 == 0:
      ret "positive even"
    el:
      ret "positive odd"
  el:
    if n % 2 == 0:
      ret "negative even"
    el:
      ret "negative odd"

print("")
print("=== Number Classifier ===")
let numbers = [-3, -2, -1, 0, 1, 2, 3]
for n in numbers:
  print(str(n) + " is " + classify_number(n))
