# tensor operations - zap's AI superpower
let a = tensor([1, 2, 3, 4, 5, 6], [2, 3])
print(a)
print(a.shape)

let b = tensor([6, 5, 4, 3, 2, 1], [2, 3])
print(a + b)
print(a * 2)

# matrix multiply
let m1 = tensor([1, 2, 3, 4], [2, 2])
let m2 = tensor([5, 6, 7, 8], [2, 2])
print(m1 @@ m2)

# pipe operator
let result = m1 |> reshape(4)
print(result)

# zeros and ones
let z = zeros(3, 3)
let o = ones(2, 4)
print(z)
print(o)
