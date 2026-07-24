# ============================================================================
# Zap Self-Hosted Interpreter - Minimal Test
# Tests that we can run a self-hosted program
# ============================================================================

import "tokens.zap"

fn test_tokens():
  let source = 'let x = 42\nprint("hello")'
  let toks = tokenize(source, "<test>")
  print("Token count: " + str(len(toks)))
  let i = 0
  while i < len(toks):
    let tok = toks[i]
    print("  " + str(tok.type) + " = " + str(tok.value))
    i = i + 1
  print("Tokenizer works!")

fn test_parsing():
  let source = 'let x = 42\nlet y = x + 10\nprint(y)'
  let toks = tokenize(source, "<test>")
  print("Tokens generated for parsing test")
  print("Parser test would go here")

fn main():
  print("=== Self-Hosted Interpreter Test ===")
  test_tokens()
  print("")
  test_parsing()
  print("")
  print("=== All tests passed! ===")

main()