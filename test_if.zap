fn classify(n):
  if n > 0:
    ret "positive"
  el:
    ret "non-positive"

print(classify(10))
print(classify(-5))
