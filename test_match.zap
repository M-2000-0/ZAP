# Test match syntax
fn get_type(ch):
  match ch:
    "(": ret "LPAREN"
    ")": ret "RPAREN"
    "{": ret "LBRACE"
    "}": ret "RBRACE"
    _: ret "UNKNOWN"

print(get_type("("))
print(get_type(")"))
print(get_type("*"))
