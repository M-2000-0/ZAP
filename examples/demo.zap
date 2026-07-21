# zap demo - all features

# 1. variables and math
let x = 42
let pi = 3.14159
print("x:", x, "pi:", pi)
print("x * pi:", x * pi)

# 2. conditionals
fn classify(n)
  if n > 0:
    ret "positive"
  el:
    ret "non-positive"

print(classify(10))
print(classify(-5))

# 3. loops
print("counting:")
for i in range(5):
  print(" ", i)

# 4. lists and dicts
let lst = [1, 2, 3, 4, 5]
print("sum:", sum(lst))
print("len:", len(lst))

let d = {name: "zap", year: 2026}
print("dict:", d)

# 5. higher-order functions (map/filter via pipe)
let nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

fn is_even(n) n % 2 == 0
fn square(n) n * n

let result = nums |> filter(is_even) |> map(square)
print("even squares:", result)

# 6. tensors
print("\n-- tensor ops --")
let t = tensor([1, 2, 3, 4, 5, 6], [2, 3])
print("tensor:", t)
print("shape:", t.shape)
print("t + 10:", t + 10)
print("t * 2:", t * 2)

# matrix multiply
let a = tensor([1, 2, 3, 4], [2, 2])
let b = tensor([5, 6, 7, 8], [2, 2])
print("a @@ b:", a @@ b)

# pipe with tensors
let flat = a |> reshape(4)
print("flattened:", flat)

# zeros/ones
print("zeros:", zeros(2, 3))
print("ones:", ones(3, 2))

# 7. classes
class Animal:
  fn init(self, name)
    self.name = name
  fn speak(self)
    print(self.name, "says hello!")

let dog = Animal("Buddy")
dog.speak()

# 8. match
fn describe(n)
  match n:
    0:
      print("zero")
    1:
      print("one")
    el:
      print("many")

describe(0)
describe(1)
describe(42)

print("\n--- zap is ready! ---")
