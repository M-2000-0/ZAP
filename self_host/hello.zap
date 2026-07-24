let name = "Zap"
let v = 42

print("Hello from self-hosted Zap!")
print("Name: $name")
print("Version: $v")

fn add(a, b):
  ret a + b

fn sub(a, b):
  ret a - b

fn multiply(a, b):
  ret a * b

fn divide(a, b):
  ret a / b

let result = add(10, 20)
print("10 + 20 = $result")

let sum = 0
let nums = [1, 2, 3, 4, 5]
for i in range(len(nums)):
  sum = sum + nums[i]
print("Sum of 1-5: $sum")

if result > 25:
  print("Result is greater than 25")
el:
  print("Result is 25 or less")
