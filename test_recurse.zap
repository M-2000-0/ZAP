fn repeat(s, n)
  if n <= 0 "" el s + repeat(s, n - 1)

print(repeat("x", 5))
