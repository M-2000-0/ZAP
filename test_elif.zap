# Test elif equivalent in Zap
fn classify(n):
  if n > 0:
    ret "positive"
  el:
    if n == 0:
      ret "zero"
    el:
      ret "negative"

print(classify(5))
print(classify(0))
print(classify(-3))
