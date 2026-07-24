# Test el if chain (el + if = elif)
fn get_type(ch):
  if ch == "(":
    ret "LPAREN"
  el:
    if ch == ")":
      ret "RPAREN"
    el:
      if ch == "{":
        ret "LBRACE"
      el:
        ret "UNKNOWN"

print(get_type("("))
print(get_type(")"))
print(get_type("*"))
