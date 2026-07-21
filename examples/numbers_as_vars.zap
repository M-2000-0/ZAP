# numbers can be variable names - great for beginners!
let 1 = "hello world"
say("variable 1 =", get("1"))

# assign to numbers without let
2 = 42
say("variable 2 =", get("2"))

# chain them like named variables
3 = 1
say("variable 3 =", get("3"))

# named variables work as usual
let x = 5
x = "five"
say("x =", x)

# step-by-step reasoning with named steps
step1 = "load data"
step2 = "process data"
step3 = "train model"
step4 = "deploy"
say("step 1:", step1)
say("step 4:", step4)

# numbers as var names in expressions
let a = 10
10 = a * 2
say("variable 10 =", get("10"))
