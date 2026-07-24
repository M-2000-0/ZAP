# Test dict access with missing keys
let d = {"a": 1, "b": 2}
print(d["a"])
print(d["b"])

# How to handle missing keys?
let val = get(d, "c")
print("missing: " + str(val))
