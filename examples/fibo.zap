fn fib(n)
  if n <= 1:
    ret n
  ret fib(n - 1) + fib(n - 2)

for i in range(10):
  print(fib(i))
