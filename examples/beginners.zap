# ZAP for beginners - no hard rules, just code

# numbers as variable names (use get("name") to read them)
1 = "hello world"
say("variable 1 =", get("1"))

# symbols as variable names
let + = "addition"
let - = "subtraction"
let * = "multiplication"
say("variable + =", get("+"))
say("variable - =", get("-"))
say("variable * =", get("*"))

# no let needed - just assign
name = "zap"
version = 1.0
say("welcome to", name, "v", version)

# beginner-friendly builtins
show("this is show")
now = now()
say("current time:", now)

# numbers as step labels
1 = "load data"
2 = "process"
3 = "train"
4 = "deploy"

# print them
say("step 1:", 1)
say("step 4:", 4)

# everything works with pipe
nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

fn is_even(n) n % 2 == 0
fn square(n) n * n

result = nums |> filter(is_even) |> map(square)
say("even squares:", result)

# tensors for AI stuff
t = tensor([1, 2, 3, 4, 5, 6], [2, 3])
show("tensor:", t)
show("shape:", t.shape)
