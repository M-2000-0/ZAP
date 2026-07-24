# List comprehension
let nums = [1, 2, 3, 4, 5]
let doubled = [x * 2 for x in nums]
print("Doubled:", doubled)

# Filtered comprehension
let evens = [x for x in nums if x % 2 == 0]
print("Evens:", evens)

# Dict comprehension
let squares = {x: x * x for x in nums}
print("Squares:", squares)

# String comprehension
let words = ["hello", "world"]
let upper = [w.upper() for w in words]
print("Upper:", upper)

# Nested
let matrix = [[1, 2], [3, 4]]
let flat = [x for row in matrix for x in row]
print("Flat:", flat)
