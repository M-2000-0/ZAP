# Test dict lookup approach
let symbol_types = {
  "(": "LPAREN",
  ")": "RPAREN",
  "{": "LBRACE",
  "}": "RBRACE",
  "[": "LBRACKET",
  "]": "RBRACKET",
  ",": "COMMA",
  ".": "DOT",
  ":": "COLON",
  "+": "PLUS",
  "-": "MINUS",
  "*": "STAR",
  "/": "SLASH",
  "%": "PERCENT",
  "<": "LT",
  ">": "GT",
  "=": "EQ",
  "!": "NOT",
}

fn get_type(ch):
  let result = symbol_types[ch]
  if result == none:
    ret "UNKNOWN"
  ret result

print(get_type("("))
print(get_type(")"))
print(get_type("*"))
print(get_type("~"))
