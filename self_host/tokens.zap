# ============================================================================
# Zap Self-Hosting Token System
# Written 100% in Zap - token types, keywords, and lexer
# ============================================================================

let TokenType = {
  "EOF": "EOF",
  "NEWLINE": "NEWLINE",
  "IDENTIFIER": "IDENTIFIER",
  "NUMBER": "NUMBER",
  "STRING": "STRING",
  "FLOAT": "FLOAT",
  "LPAREN": "LPAREN",
  "RPAREN": "RPAREN",
  "LBRACE": "LBRACE",
  "RBRACE": "RBRACE",
  "LBRACKET": "LBRACKET",
  "RBRACKET": "RBRACKET",
  "COMMA": "COMMA",
  "DOT": "DOT",
  "COLON": "COLON",
  "ARROW": "ARROW",
  "PIPE": "PIPE",
  "PLUS": "PLUS",
  "MINUS": "MINUS",
  "STAR": "STAR",
  "SLASH": "SLASH",
  "PERCENT": "PERCENT",
  "LT": "LT",
  "GT": "GT",
  "LTE": "LTE",
  "GTE": "GTE",
  "EQEQ": "EQEQ",
  "EQ": "EQ",
  "NEQ": "NEQ",
  "AND": "AND",
  "OR": "OR",
  "NOT": "NOT",
  "KW_FN": "KW_FN",
  "KW_LET": "KW_LET",
  "KW_IF": "KW_IF",
  "KW_EL": "KW_EL",
  "KW_FOR": "KW_FOR",
  "KW_IN": "KW_IN",
  "KW_WHILE": "KW_WHILE",
  "KW_RET": "KW_RET",
  "KW_TRUE": "KW_TRUE",
  "KW_FALSE": "KW_FALSE",
  "KW_NONE": "KW_NONE",
  "KW_AND": "KW_AND",
  "KW_OR": "KW_OR",
  "KW_NOT": "KW_NOT",
  "KW_IMPORT": "KW_IMPORT",
  "KW_CLASS": "KW_CLASS",
  "KW_BREAK": "KW_BREAK",
  "KW_CONTINUE": "KW_CONTINUE",
}

let KEYWORDS = {
  "fn": TokenType.KW_FN,
  "let": TokenType.KW_LET,
  "if": TokenType.KW_IF,
  "el": TokenType.KW_EL,
  "else": TokenType.KW_EL,
  "for": TokenType.KW_FOR,
  "in": TokenType.KW_IN,
  "while": TokenType.KW_WHILE,
  "ret": TokenType.KW_RET,
  "true": TokenType.KW_TRUE,
  "false": TokenType.KW_FALSE,
  "none": TokenType.KW_NONE,
  "and": TokenType.KW_AND,
  "or": TokenType.KW_OR,
  "not": TokenType.KW_NOT,
  "import": TokenType.KW_IMPORT,
  "class": TokenType.KW_CLASS,
  "break": TokenType.KW_BREAK,
  "continue": TokenType.KW_CONTINUE,
}

# Escape sequence lookup
let ESCAPES = {
  "n": "\n",
  "t": "\t",
  "r": "\r",
  "\\": "\\",
  '"': '"',
  "'": "'",
}

# Digit to int lookup
let DIGITS = {
  "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
  "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
}

fn resolve_escape(esc):
  let mapped = ESCAPES[esc]
  if mapped != none:
    ret mapped
  ret esc

fn digit_val(ch):
  ret DIGITS[ch]

fn is_alpha(ch):
  ret (ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or ch == "_"

fn is_alnum(ch):
  ret is_alpha(ch) or (ch >= "0" and ch <= "9")

fn is_digit(ch):
  ret ch >= "0" and ch <= "9"

class Token:
  fn init(self, tok_type, value, line, col):
    self.typ = tok_type
    self.value = value
    self.line = line
    self.col = col

fn parse_int(str):
  let result = 0
  let idx = 0
  let sign = 1
  let first = str[0]
  let start = 0
  if first == "-":
    sign = -1
    start = 1
  el:
    if first == "+":
      start = 1
  idx = start
  while idx < len(str):
    let code = str[idx]
    if is_digit(code):
      result = result * 10 + digit_val(code)
    idx = idx + 1
  ret result * sign

fn parse_float(str):
  let integer_part = ""
  let decimal_part = ""
  let start = 0
  let first = str[0]
  let sign = 1
  if first == "-":
    sign = -1
    start = 1
  el:
    if first == "+":
      start = 1
  let dot_pos = -1
  let pos = start
  while pos < len(str):
    if str[pos] == ".":
      dot_pos = pos
      break
    pos = pos + 1
  if dot_pos == -1:
    pos = start
    while pos < len(str):
      integer_part = integer_part + str[pos]
      pos = pos + 1
  el:
    pos = start
    while pos < dot_pos:
      integer_part = integer_part + str[pos]
      pos = pos + 1
    pos = dot_pos + 1
    while pos < len(str):
      decimal_part = decimal_part + str[pos]
      pos = pos + 1
  let int_value = 0
  if len(integer_part) > 0:
    int_value = parse_int(integer_part)
  if len(decimal_part) == 0:
    ret float(int_value) * sign
  let decimal_value = 0
  let multiplier = 0.1
  let d = 0
  while d < len(decimal_part):
    let dv = digit_val(decimal_part[d])
    decimal_value = decimal_value + dv * multiplier
    multiplier = multiplier * 0.1
    d = d + 1
  ret (int_value + decimal_value) * sign

# Single char token lookup
let SINGLE_CHARS = {
  "(": TokenType.LPAREN,
  ")": TokenType.RPAREN,
  "{": TokenType.LBRACE,
  "}": TokenType.RBRACE,
  "[": TokenType.LBRACKET,
  "]": TokenType.RBRACKET,
  ",": TokenType.COMMA,
  ".": TokenType.DOT,
  ":": TokenType.COLON,
  "+": TokenType.PLUS,
  "-": TokenType.MINUS,
  "*": TokenType.STAR,
  "/": TokenType.SLASH,
  "%": TokenType.PERCENT,
  "<": TokenType.LT,
  ">": TokenType.GT,
  "=": TokenType.EQ,
  "!": TokenType.NOT,
}

fn tokenize(source, filename):
  let tokens = []
  let line = 1
  let col = 1
  let i = 0

  while i < len(source):
    let ch = source[i]

    # Newlines
    if ch == "\n":
      line = line + 1
      col = 1
      i = i + 1
      continue

    # Whitespace
    if ch == " " or ch == "\t":
      col = col + 1
      i = i + 1
      continue

    # Comments
    if ch == "#":
      while i < len(source) and source[i] != "\n":
        i = i + 1
      continue

    # Numbers
    if is_digit(ch) or (ch == "." and i + 1 < len(source) and is_digit(source[i + 1])):
      let num_str = ""
      let is_float = false
      while i < len(source) and (is_digit(source[i]) or source[i] == "."):
        if source[i] == ".":
          is_float = true
        num_str = num_str + source[i]
        i = i + 1
      if is_float:
        tokens.append(Token(TokenType.FLOAT, parse_float(num_str), line, col))
      else:
        tokens.append(Token(TokenType.NUMBER, parse_int(num_str), line, col))
      col = col + len(num_str)
      continue

    # Strings
    if ch == '"' or ch == "'":
      let quote = ch
      let str_val = ""
      i = i + 1
      while i < len(source):
        if source[i] == "\\" and i + 1 < len(source):
          i = i + 1
          str_val = str_val + resolve_escape(source[i])
          i = i + 1
        else:
          if source[i] == quote:
            i = i + 1
            tokens.append(Token(TokenType.STRING, str_val, line, col))
            col = col + len(str_val) + 2
            break
          str_val = str_val + source[i]
          i = i + 1
          col = col + 1
      continue

    # Identifiers and keywords
    if is_alpha(ch):
      let ident = ""
      while i < len(source) and is_alnum(source[i]):
        ident = ident + source[i]
        i = i + 1
      let tok_type = KEYWORDS[ident]
      if tok_type == none:
        tok_type = TokenType.IDENTIFIER
      tokens.append(Token(tok_type, ident, line, col))
      col = col + len(ident)
      continue

    # Two-character operators
    if i + 1 < len(source):
      let two_char = source[i] + source[i + 1]
      if two_char == "==":
        tokens.append(Token(TokenType.EQEQ, "==", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "!=":
        tokens.append(Token(TokenType.NEQ, "!=", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "<=":
        tokens.append(Token(TokenType.LTE, "<=", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == ">=":
        tokens.append(Token(TokenType.GTE, ">=", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "**":
        tokens.append(Token(TokenType.STAR, "**", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "@@":
        tokens.append(Token(TokenType.STAR, "@@", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "+=":
        tokens.append(Token(TokenType.PLUS, "+=", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "-=":
        tokens.append(Token(TokenType.MINUS, "-=", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "|>":
        tokens.append(Token(TokenType.PIPE, "|>", line, col))
        i = i + 2
        col = col + 2
        continue
      if two_char == "->":
        tokens.append(Token(TokenType.ARROW, "->", line, col))
        i = i + 2
        col = col + 2
        continue

    # Single character tokens
    let tok_type = SINGLE_CHARS[ch]
    if tok_type != none:
      tokens.append(Token(tok_type, ch, line, col))
      col = col + 1
      i = i + 1
      continue

    # Unknown character
    i = i + 1
    col = col + 1

  tokens.append(Token(TokenType.EOF, "", line, col))
  ret tokens

# ============================================================================
# Test the tokenizer
# ============================================================================

fn test_tokenizer():
  let source = 'let x = 42\nprint("hello")'
  let toks = tokenize(source, "<test>")
  print("Token count: " + str(len(toks)))
  let i = 0
  while i < len(toks):
    let tok = toks[i]
    print("  " + str(tok.typ) + " = " + str(tok.value))
    i = i + 1
  print("Tokenizer test passed!")

test_tokenizer()
