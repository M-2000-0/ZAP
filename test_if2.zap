# Test if/elif chain
fn get_type(ch):
  if ch == "(":
    ret "LPAREN"
  elif ch == ")":
    ret "RPAREN"
  elif ch == "{":
    ret "LBRACE"
  else:
    ret "UNKNOWN"

print(get_type("("))
print(get_type(")"))
print(get_type("*"))
