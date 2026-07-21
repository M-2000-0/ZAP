from .tokens import Token, TokenType, KEYWORDS

class Lexer:
    def __init__(self, source, filename='<stdin>'):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.indent_stack = [0]
        self._bracket_depth = 0

    def _in_brackets(self):
        return self._bracket_depth > 0

    def error(self, msg):
        raise SyntaxError(f"{self.filename}:{self.line}:{self.col}: {msg}")

    def peek(self, offset=0):
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else '\0'

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        self.col += 1
        return ch

    def skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in ' \t':
            self.advance()

    def read_number(self):
        start = self.pos
        is_float = False
        while self.peek().isdigit():
            self.advance()
        if self.peek() == '.':
            is_float = True
            self.advance()
            while self.peek().isdigit():
                self.advance()
        if self.peek() in 'eE':
            is_float = True
            self.advance()
            if self.peek() in '+-':
                self.advance()
            while self.peek().isdigit():
                self.advance()
        val = self.source[start:self.pos]
        return Token(TokenType.FLOAT if is_float else TokenType.NUMBER,
                     float(val) if is_float else int(val),
                     self.line, start)

    def read_string(self, quote):
        start = self.pos
        self.pos += 1  # skip opening quote
        s = ''
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            self.pos += 1
            self.col += 1
            if ch == quote:
                return Token(TokenType.STRING, s, self.line, start)
            if ch == '\\':
                esc = self.source[self.pos]
                self.pos += 1
                self.col += 1
                esc_map = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0',
                          "'": "'", '"': '"', '\\': '\\'}
                s += esc_map.get(esc, esc)
            else:
                s += ch
        self.error("unterminated string")

    def read_identifier(self):
        start = self.pos - 1
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()
        word = self.source[start:self.pos]
        tok_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
        return Token(tok_type, word, self.line, start)

    def handle_newline(self):
        self.line += 1
        self.col = 1
        return Token(TokenType.NEWLINE, '\n', self.line - 1, 0)

    def handle_indent(self, start_col):
        if start_col > self.indent_stack[-1]:
            self.indent_stack.append(start_col)
            return Token(TokenType.INDENT, start_col, self.line, start_col)
        elif start_col < self.indent_stack[-1]:
            dedents = []
            while self.indent_stack and start_col < self.indent_stack[-1]:
                self.indent_stack.pop()
                dedents.append(Token(TokenType.DEDENT, self.indent_stack[-1] if self.indent_stack else 0,
                                     self.line, start_col))
            return dedents
        return None

    def tokenize(self):
        i = 0
        while i < len(self.source):
            self.pos = i
            ch = self.source[i]

            if ch in ' \t':
                i += 1
                continue

            if ch == '#':
                while i < len(self.source) and self.source[i] != '\n':
                    i += 1
                continue

            if ch == '\n':
                if self._in_brackets():
                    i += 1
                    self.line += 1
                    self.col = 1
                    continue
                self.line += 1
                self.col = 1
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line - 1, 0))
                i += 1
                start_col = 0
                while i < len(self.source) and self.source[i] == ' ':
                    start_col += 1
                    i += 1
                if i >= len(self.source):
                    break
                if self.source[i] == '\n':
                    continue
                if self.source[i] == '#':
                    while i < len(self.source) and self.source[i] != '\n':
                        i += 1
                    continue
                indent_result = self.handle_indent(start_col)
                if indent_result:
                    if isinstance(indent_result, list):
                        self.tokens.extend(indent_result)
                    else:
                        self.tokens.append(indent_result)
                continue

            if ch.isdigit():
                tok = self.read_number()
                self.tokens.append(tok)
                i = self.pos
                continue

            if ch in '"\'':
                tok = self.read_string(ch)
                self.tokens.append(tok)
                i = self.pos
                continue

            if ch.isalpha() or ch == '_':
                self.pos = i
                self.advance()
                tok = self.read_identifier()
                self.tokens.append(tok)
                i = self.pos
                continue

            two_char = self.source[i:i+2] if i + 1 < len(self.source) else ''
            tok = None

            if two_char == '=>':
                tok = Token(TokenType.ARROW, '=>', self.line, i)
                i += 2
            elif two_char == '==':
                tok = Token(TokenType.EQEQ, '==', self.line, i)
                i += 2
            elif two_char == '!=':
                tok = Token(TokenType.NEQ, '!=', self.line, i)
                i += 2
            elif two_char == '<=':
                tok = Token(TokenType.LTE, '<=', self.line, i)
                i += 2
            elif two_char == '>=':
                tok = Token(TokenType.GTE, '>=', self.line, i)
                i += 2
            elif two_char == '::':
                tok = Token(TokenType.ASSIGN, '::', self.line, i)
                i += 2
            elif two_char == '->':
                tok = Token(TokenType.ARROW, '->', self.line, i)
                i += 2
            elif two_char == '|>':
                tok = Token(TokenType.PIPE, '|>', self.line, i)
                i += 2
            elif two_char == '**':
                tok = Token(TokenType.POW, '**', self.line, i)
                i += 2
            elif two_char == '@@':
                tok = Token(TokenType.MATMUL, '@@', self.line, i)
                i += 2
            elif two_char == '+=':
                tok = Token(TokenType.PLUS_ASSIGN, '+=', self.line, i)
                i += 2
            elif two_char == '-=':
                tok = Token(TokenType.MINUS_ASSIGN, '-=', self.line, i)
                i += 2
            elif ch == '(':
                tok = Token(TokenType.LPAREN, '(', self.line, i)
                self._bracket_depth += 1
                i += 1
            elif ch == ')':
                tok = Token(TokenType.RPAREN, ')', self.line, i)
                self._bracket_depth -= 1
                i += 1
            elif ch == '{':
                tok = Token(TokenType.LBRACE, '{', self.line, i)
                self._bracket_depth += 1
                i += 1
            elif ch == '}':
                tok = Token(TokenType.RBRACE, '}', self.line, i)
                self._bracket_depth -= 1
                i += 1
            elif ch == '[':
                tok = Token(TokenType.LBRACKET, '[', self.line, i)
                self._bracket_depth += 1
                i += 1
            elif ch == ']':
                tok = Token(TokenType.RBRACKET, ']', self.line, i)
                self._bracket_depth -= 1
                i += 1
            elif ch == ',':
                tok = Token(TokenType.COMMA, ',', self.line, i)
                i += 1
            elif ch == '.':
                tok = Token(TokenType.DOT, '.', self.line, i)
                i += 1
            elif ch == ':':
                tok = Token(TokenType.COLON, ':', self.line, i)
                i += 1
            elif ch == '+':
                tok = Token(TokenType.PLUS, '+', self.line, i)
                i += 1
            elif ch == '-':
                tok = Token(TokenType.MINUS, '-', self.line, i)
                i += 1
            elif ch == '*':
                tok = Token(TokenType.STAR, '*', self.line, i)
                i += 1
            elif ch == '/':
                tok = Token(TokenType.SLASH, '/', self.line, i)
                i += 1
            elif ch == '%':
                tok = Token(TokenType.PERCENT, '%', self.line, i)
                i += 1
            elif ch == '<':
                tok = Token(TokenType.LT, '<', self.line, i)
                i += 1
            elif ch == '>':
                tok = Token(TokenType.GT, '>', self.line, i)
                i += 1
            elif ch == '=':
                tok = Token(TokenType.EQ, '=', self.line, i)
                i += 1
            elif ch == '@':
                tok = Token(TokenType.KW_AT, '@', self.line, i)
                i += 1
            elif ch == '!':
                tok = Token(TokenType.NOT, '!', self.line, i)
                i += 1
            else:
                self.error(f"unexpected character: {ch!r}")

            if tok:
                self.tokens.append(tok)

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, self.indent_stack[-1], self.line, 0))

        self.tokens.append(Token(TokenType.EOF, None, self.line, 0))
        return self.tokens
