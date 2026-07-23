from .tokens import TokenType
from .ast_nodes import *

SYMBOL_TOKENS = {
    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
    TokenType.PERCENT, TokenType.POW, TokenType.MATMUL,
    TokenType.EQ, TokenType.EQEQ, TokenType.NEQ,
    TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE,
    TokenType.AND, TokenType.OR, TokenType.NOT,
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
    TokenType.LPAREN, TokenType.RPAREN,
    TokenType.LBRACE, TokenType.RBRACE,
    TokenType.LBRACKET, TokenType.RBRACKET,
    TokenType.COMMA, TokenType.DOT, TokenType.COLON,
    TokenType.ARROW, TokenType.PIPE,
}

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self._indents = [0]
        self.errors = []
        self.recovery_mode = False

    # Statement-start tokens for error recovery skip-ahead
    STMT_START = {
        TokenType.KW_LET, TokenType.KW_FN, TokenType.KW_IF, TokenType.KW_FOR,
        TokenType.KW_WHILE, TokenType.KW_RET, TokenType.KW_IMPORT,
        TokenType.KW_CLASS, TokenType.KW_MATCH, TokenType.KW_ASYNC,
        TokenType.KW_INTEND, TokenType.KW_AT, TokenType.KW_SERVICE,
        TokenType.KW_DATABASE, TokenType.KW_API, TokenType.KW_PAGE,
        TokenType.KW_SCHEMA, TokenType.KW_MODEL, TokenType.KW_PERMISSION,
        TokenType.KW_CONCURRENT, TokenType.KW_CHECK, TokenType.KW_INVARIANT,
        TokenType.KW_EXPECT, TokenType.KW_VERSION, TokenType.KW_BREAK,
        TokenType.KW_CONTINUE, TokenType.DEDENT,
    }

    def error(self, msg):
        tok = self.peek()
        err = SyntaxError(f"parse error at L{tok.line}:{tok.col}: {msg}")
        if self.recovery_mode:
            self.errors.append(err)
            return None  # caller should check for None and sync
        raise err

    def sync(self, target_indent=None):
        """Skip tokens until a statement boundary is reached."""
        depth = 0
        while self.pos < len(self.tokens):
            tok = self.peek()
            if target_indent is not None and tok.type == TokenType.DEDENT and tok.value <= target_indent:
                return
            if depth == 0 and tok.type in self.STMT_START:
                return
            if tok.type == TokenType.EOF:
                return
            if tok.type == TokenType.INDENT:
                depth += 1
            elif tok.type == TokenType.DEDENT:
                depth -= 1
                if depth < 0:
                    depth = 0
                    if target_indent is not None and tok.value <= target_indent:
                        return
            self.advance()

    def peek(self, offset=0):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, *types):
        tok = self.peek()
        if tok.type not in types:
            self.error(f"expected {[t.name for t in types]}, got {tok.type.name} ('{tok.value}')")
        return self.advance()

    def match(self, *types):
        if self.peek().type in types:
            return self.advance()
        return None

    def skip_newlines(self):
        while self.peek().type == TokenType.NEWLINE:
            self.advance()

    def parse(self):
        stmts = self.parse_top_block()
        return Program(stmts)

    def parse_top_block(self):
        stmts = []
        self.skip_newlines()
        while self.peek().type not in (TokenType.EOF, TokenType.DEDENT):
            try:
                stmt = self.parse_stmt()
                if stmt:
                    stmts.append(stmt)
            except SyntaxError as e:
                if self.recovery_mode:
                    self.errors.append(e)
                    self.sync()
                else:
                    raise
            self.skip_newlines()
            if self.peek().type in (TokenType.DEDENT, TokenType.EOF):
                break
        return stmts

    # indent tracking: [0] initially, push INDENT value when entering block,
    # consume DEDENTs when leaving, pop when target level matches current level
    def parse_block(self):
        self.skip_newlines()
        try:
            indent_tok = self.expect(TokenType.INDENT)
        except SyntaxError as e:
            if self.recovery_mode:
                self.errors.append(e)
                return []
            raise
        self._indents.append(indent_tok.value)
        stmts = []
        self.skip_newlines()
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            try:
                stmt = self.parse_stmt()
                if stmt:
                    stmts.append(stmt)
            except SyntaxError as e:
                if self.recovery_mode:
                    self.errors.append(e)
                    self.sync()
                else:
                    raise
            self.skip_newlines()
            if self.peek().type in (TokenType.DEDENT, TokenType.EOF):
                break
        while self.peek().type == TokenType.DEDENT:
            d = self.advance()
            try:
                target = self._indents[-1]
            except IndexError:
                break
            if not isinstance(d.value, (int, float)):
                break
            if not isinstance(target, (int, float)):
                break
            if d.value == target:
                break
            if d.value < target:
                while self._indents and isinstance(self._indents[-1], (int, float)) and self._indents[-1] > d.value:
                    self._indents.pop()
                break
        return stmts

    def parse_stmt(self):
        tok = self.peek()

        if tok.type == TokenType.KW_LET:
            return self.parse_let()
        if tok.type == TokenType.KW_AT:
            return self.parse_decorated()
        if tok.type == TokenType.KW_FN:
            return self.parse_fn_def()
        if tok.type == TokenType.KW_IF:
            return self.parse_if()
        if tok.type == TokenType.KW_FOR:
            return self.parse_for()
        if tok.type == TokenType.KW_WHILE:
            return self.parse_while()
        if tok.type == TokenType.KW_RET:
            return self.parse_ret()
        if tok.type == TokenType.KW_IMPORT:
            return self.parse_import()
        if tok.type == TokenType.KW_CLASS:
            return self.parse_class()
        if tok.type == TokenType.KW_MATCH:
            return self.parse_match()
        if tok.type == TokenType.KW_ASYNC:
            return self.parse_async_fn()
        if tok.type == TokenType.KW_INTEND:
            return self.parse_intend()
        if tok.type == TokenType.KW_SERVICE:
            return self.parse_service()
        if tok.type == TokenType.KW_DATABASE:
            return self.parse_database()
        if tok.type == TokenType.KW_API:
            return self.parse_api()
        if tok.type == TokenType.KW_PAGE:
            return self.parse_page()
        if tok.type == TokenType.KW_SCHEMA:
            return self.parse_schema()
        if tok.type == TokenType.KW_MODEL:
            return self.parse_model()

        # AI-native features (only standalone ones; requires/ensures inside fn body)
        if tok.type == TokenType.KW_PERMISSION:
            return self.parse_permission()
        if tok.type == TokenType.KW_CONCURRENT:
            return self.parse_concurrent()
        if tok.type == TokenType.KW_CHECK:
            return self.parse_check()
        if tok.type == TokenType.KW_INVARIANT:
            return self.parse_invariant()
        if tok.type == TokenType.KW_EXPECT:
            return self.parse_expect()
        if tok.type == TokenType.KW_VERSION:
            # If followed by '=', treat as assignment expression, not version annotation
            if self.peek(1) and self.peek(1).type == TokenType.EQ:
                return self.parse_expr_stmt()
            return self.parse_version()

        if tok.type == TokenType.KW_BREAK:
            return self.parse_break()
        if tok.type == TokenType.KW_CONTINUE:
            return self.parse_continue()

        if tok.type == TokenType.NEWLINE:
            self.advance()
            return None

        return self.parse_expr_stmt()

    def _expect_name(self):
        """Expect an identifier or keyword token for use as a name."""
        tok = self.peek()
        if tok.type == TokenType.IDENTIFIER or tok.type.name.startswith('KW_'):
            self.pos += 1
            return tok
        return self.expect(TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.FLOAT, *SYMBOL_TOKENS)

    def parse_let(self):
        tok = self.advance()
        name_tok = self._expect_name()
        name = str(name_tok.value)
        type_ann = None
        if self.match(TokenType.COLON):
            type_ann = self.expect(TokenType.IDENTIFIER).value
        value = None
        if self.match(TokenType.EQ):
            value = self.parse_expr()
        return LetStmt(name, value, type_ann, tok.line, tok.col)

    def parse_decorated(self):
        decorators = []
        contracts = []
        while self.peek().type == TokenType.KW_AT:
            tok = self.advance()
            name = self.expect(TokenType.IDENTIFIER, TokenType.KW_REQUIRES, TokenType.KW_ENSURES).value
            args = []
            if self.match(TokenType.LPAREN):
                if self.peek().type != TokenType.RPAREN:
                    args.append(self.parse_expr())
                    while self.match(TokenType.COMMA):
                        if self.peek().type == TokenType.RPAREN:
                            break
                        args.append(self.parse_expr())
                self.expect(TokenType.RPAREN)
            self.expect(TokenType.NEWLINE)
            if name in ('requires', 'ensures', 'req', 'ens'):
                cond = args[0] if args else Literal(True)
                contracts.append(ContractAnnotation(name, cond, tok.line, tok.col))
            else:
                decorators.append(Decorator(name, args, tok.line, tok.col))
        if self.peek().type == TokenType.KW_FN:
            fn = self.parse_fn_def()
            fn.decorators = decorators
            fn.contracts = contracts
            return fn
        raise SyntaxError(f"decorator must precede fn definition")

    def parse_fn_def(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER)
        return self.parse_fn_body(name.value, is_async=False, tok=tok)

    def parse_async_fn(self):
        tok = self.advance()
        if self.peek().type == TokenType.KW_FN:
            self.advance()
        name = self.expect(TokenType.IDENTIFIER)
        return self.parse_fn_body(name.value, is_async=True, tok=tok)

    def parse_intend(self):
        tok = self.advance()
        if self.peek().type == TokenType.STRING:
            text = self.advance().value
            return IntendStmt(text, tok.line, tok.col)
        else:
            expr = self.parse_expr()
            return IntendStmt(str(expr), tok.line, tok.col)

    def parse_service(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        methods = []
        expose = []
        metadata = {}
        version = None
        permissions = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            self.skip_newlines()
            if self.peek().type in (TokenType.DEDENT, TokenType.EOF):
                break
            if self.match(TokenType.KW_EXPOSE):
                expose.append(self.expect(TokenType.IDENTIFIER).value)
                self.expect(TokenType.NEWLINE)
            elif self.peek().type == TokenType.KW_VERSION:
                version = self.parse_version_value()
            elif self.peek().type in (TokenType.KW_REQUIRES, TokenType.KW_GUARANTEES):
                section_kind = 'requires' if self.peek().type == TokenType.KW_REQUIRES else 'guarantees'
                self.parse_metadata_section(metadata, section_kind)
            elif self.peek().type == TokenType.KW_PERMISSION:
                perm = self.parse_permission()
                permissions.append(perm)
            elif self.peek().type == TokenType.KW_FN:
                methods.append(self.parse_fn_def())
            else:
                break
        self._consume_dedents()
        return ServiceDecl(name, methods, expose, metadata, version, permissions, tok.line, tok.col)

    def parse_database(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        tables = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_SCHEMA:
                tables.append(self.parse_schema())
            else:
                break
        self._consume_dedents()
        return DatabaseDecl(name, tables, tok.line, tok.col)

    def parse_api(self):
        tok = self.advance()
        methods_map = {'GET': 'GET', 'POST': 'POST', 'PUT': 'PUT', 'DELETE': 'DELETE', 'PATCH': 'PATCH'}
        method = self.expect(TokenType.IDENTIFIER).value
        if method.upper() not in methods_map:
            self.error(f"expected HTTP method (GET/POST/PUT/DELETE/PATCH), got '{method}'")
        method = method.upper()
        path = '/'
        if self.peek().type == TokenType.STRING:
            path = self.advance().value
        elif self.peek().type == TokenType.SLASH:
            path_tokens = []
            while self.peek().type in (TokenType.SLASH, TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.LBRACE, TokenType.RBRACE):
                path_tokens.append(str(self.advance().value))
            path = ''.join(path_tokens)
        if self.match(TokenType.ARROW):
            returns = self.expect(TokenType.IDENTIFIER).value
        else:
            returns = None
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        handler = None
        params = []
        version = None
        permissions = []
        contracts = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_FN:
                handler = self.parse_fn_def()
            elif self.peek().type == TokenType.KW_LET:
                let_stmt = self.parse_let()
                if let_stmt.name:
                    params.append({'name': let_stmt.name, 'type': let_stmt.type_annotation, 'default': let_stmt.value})
            elif self.peek().type == TokenType.KW_VERSION:
                version = self.parse_version_value()
            elif self.peek().type == TokenType.KW_PERMISSION:
                permissions.append(self.parse_permission())
            elif self.peek().type in (TokenType.KW_REQUIRES, TokenType.KW_ENSURES):
                kind = 'requires' if self.peek().type == TokenType.KW_REQUIRES else 'ensures'
                cl = self.parse_contract_clause()
                contracts.append(cl)
            else:
                break
        self._consume_dedents()
        return ApiEndpoint(method, path, handler, params, returns, version, permissions, contracts, tok.line, tok.col)

    def parse_page(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        route = '/'
        if self.peek().type == TokenType.STRING:
            route = self.advance().value
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        components = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            stmt = self.parse_stmt()
            if stmt:
                components.append(stmt)
            self.skip_newlines()
        self._consume_dedents()
        return PageDecl(name, route, components, tok.line, tok.col)

    def parse_schema(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        fields = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.IDENTIFIER:
                field_name = self.advance().value
                self.expect(TokenType.COLON)
                field_type = self.expect(TokenType.IDENTIFIER).value
                constraints = []
                if self.peek().type == TokenType.EQ:
                    self.advance()
                    default_val = self.parse_expr()
                    constraints.append(('default', default_val))
                elif self.peek().type == TokenType.STRING:
                    desc = self.advance().value
                    constraints.append(('desc', desc))
                fields.append(SchemaField(field_name, field_type, constraints))
                self.expect(TokenType.NEWLINE)
            else:
                break
        self._consume_dedents()
        return SchemaDecl(name, fields, tok.line, tok.col)

    def parse_model(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        fields = []
        methods = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_FN:
                methods.append(self.parse_fn_def())
            elif self.peek().type == TokenType.IDENTIFIER:
                peek2 = self.peek(1)
                if peek2 and peek2.type == TokenType.COLON:
                    field_name = self.advance().value
                    self.advance()
                    field_type = self.expect(TokenType.IDENTIFIER).value
                    constraints = []
                    if self.peek().type == TokenType.EQ:
                        self.advance()
                        default_val = self.parse_expr()
                        constraints.append(('default', default_val))
                    fields.append(SchemaField(field_name, field_type, constraints))
                    self.expect(TokenType.NEWLINE)
                else:
                    break
            else:
                break
        self._consume_dedents()
        return ModelDecl(name, fields, methods, tok.line, tok.col)

    def parse_version_value(self):
        """Parse: version STRING, return VersionAnn node."""
        tok = self.advance()  # 'version'
        val = self.expect(TokenType.STRING).value
        self.expect(TokenType.NEWLINE)
        return VersionAnn(val, tok.line, tok.col)

    def parse_contract_clause(self):
        """requires/ensures expression NEWLINE"""
        kind = 'requires' if self.peek().type == TokenType.KW_REQUIRES else 'ensures'
        self.advance()
        cond = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return ContractClause(kind, cond, self.peek().line, self.peek().col)

    def parse_metadata_section(self, metadata, kind):
        """Parse: requires:/guarantees: then indented list of conditions."""
        self.advance()  # 'requires' or 'guarantees'
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        conditions = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            cond = self.parse_expr()
            conditions.append(cond)
            self.expect(TokenType.NEWLINE)
            self.skip_newlines()
        self._consume_dedents()
        metadata[kind] = conditions

    def parse_permission(self):
        """permission name [description]"""
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        desc = ''
        if self.peek().type == TokenType.STRING:
            desc = self.advance().value
        self.expect(TokenType.NEWLINE)
        return PermissionDecl(name, desc, tok.line, tok.col)

    def parse_concurrent(self):
        """concurrent COLON NEWLINE INDENT branches DEDENT"""
        tok = self.advance()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        branches = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            self.skip_newlines()
            if self.peek().type in (TokenType.DEDENT, TokenType.EOF):
                break
            stmts = []
            while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
                stmt = self.parse_stmt()
                if stmt:
                    stmts.append(stmt)
                self.skip_newlines()
                if self.peek().type == TokenType.DEDENT:
                    break
            if stmts:
                branches.append(Block(stmts))
        self._consume_dedents()
        return ConcurrentBlock(branches, tok.line, tok.col)

    def parse_check(self):
        """check COLON NEWLINE INDENT expect+ DEDENT"""
        tok = self.advance()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        assertions = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_EXPECT:
                assertions.append(self.parse_expect())
            else:
                cond = self.parse_expr()
                assertions.append(cond)
                self.expect(TokenType.NEWLINE)
            self.skip_newlines()
        self._consume_dedents()
        return CheckBlock(assertions, tok.line, tok.col)

    def parse_invariant(self):
        """invariant expression"""
        tok = self.advance()
        cond = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return InvariantStmt(cond, tok.line, tok.col)

    def parse_expect(self):
        """expect expression [STRING]"""
        tok = self.advance()
        cond = self.parse_expr()
        msg = ''
        if self.peek().type == TokenType.STRING:
            msg = self.advance().value
        self.expect(TokenType.NEWLINE)
        return ExpectStmt(cond, msg, tok.line, tok.col)

    def parse_version(self):
        """version STRING"""
        return self.parse_version_value()

    def _consume_dedents(self):
        target = self._indents[-1] if self._indents else 0
        self.skip_newlines()
        while self.peek().type == TokenType.DEDENT:
            d = self.advance()
            if not isinstance(d.value, (int, float)) or not isinstance(target, (int, float)):
                break
            if d.value == target:
                break
            if d.value < target:
                while self._indents and isinstance(self._indents[-1], (int, float)) and self._indents[-1] > d.value:
                    self._indents.pop()
                break

    def parse_fn_body(self, name, is_async=False, tok=None):
        line, col = tok.line, tok.col if tok else (1, 1)
        self.expect(TokenType.LPAREN)
        params = []
        if self.peek().type != TokenType.RPAREN:
            params.append(self.parse_param())
            while self.match(TokenType.COMMA):
                if self.peek().type == TokenType.RPAREN:
                    break
                params.append(self.parse_param())
        self.expect(TokenType.RPAREN)
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.expect(TokenType.IDENTIFIER).value

        if self.peek().type == TokenType.COLON:
            self.advance()
            self.expect(TokenType.NEWLINE)
            body = Block(self.parse_block(), line, col)
            return FnDef(name, params, body, return_type, is_async, line, col)

        # Block body with optional contract clauses
        contracts = []
        if self.peek().type == TokenType.NEWLINE:
            self.advance()
            self.skip_newlines()
            indent_tok = self.expect(TokenType.INDENT)
            fn_indent = indent_tok.value
            self._indents.append(fn_indent)

            # Parse contract clauses (requires/ensures) before regular statements
            self.skip_newlines()
            while self.peek().type in (TokenType.KW_REQUIRES, TokenType.KW_ENSURES):
                kind = 'requires' if self.peek().type == TokenType.KW_REQUIRES else 'ensures'
                self.advance()
                cond = self.parse_expr()
                self.expect(TokenType.NEWLINE)
                self.skip_newlines()
                contracts.append(ContractClause(kind, cond, line, col))

            # Parse the rest of the block (regular statements)
            stmts = []
            while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
                try:
                    stmt = self.parse_stmt()
                    if stmt:
                        stmts.append(stmt)
                except SyntaxError as e:
                    if self.recovery_mode:
                        self.errors.append(e)
                        self.sync(target_indent=fn_indent)
                    else:
                        raise
                self.skip_newlines()
                if self.peek().type in (TokenType.DEDENT, TokenType.EOF):
                    break

            # Consume DEDENTs back to this fn block's indent level only
            self.skip_newlines()
            while self.peek().type == TokenType.DEDENT:
                d = self.advance()
                if d.value == fn_indent:
                    break
                if d.value < fn_indent:
                    # Pop indents but stop at the level before fn block
                    while len(self._indents) > 1 and self._indents[-1] > d.value:
                        self._indents.pop()
                    break
            body = Block(stmts, line, col)
            return FnDef(name, params, body, return_type, is_async, line, col, contracts=contracts)

        if self.peek().type == TokenType.KW_RET:
            body = Block([self.parse_ret()], line, col)
            return FnDef(name, params, body, return_type, is_async, line, col, contracts=contracts)

        body = Block([self.parse_expr_stmt()], line, col)
        return FnDef(name, params, body, return_type, is_async, line, col, contracts=contracts)

    def parse_param(self):
        name = self.expect(TokenType.IDENTIFIER)
        type_ann = None
        if self.match(TokenType.COLON):
            type_ann = self.expect(TokenType.IDENTIFIER).value
        default = None
        if self.match(TokenType.EQ):
            default = self.parse_expr()
        return {'name': name.value, 'type': type_ann, 'default': default}

    def parse_if(self):
        tok = self.advance()
        cond = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = Block(self.parse_block(), tok.line, tok.col)
        else_body = None
        if self.peek().type == TokenType.KW_EL:
            self.advance()
            if self.match(TokenType.KW_IF):
                else_body = self.parse_if()
            else:
                self.expect(TokenType.COLON)
                self.expect(TokenType.NEWLINE)
                else_body = Block(self.parse_block(), tok.line, tok.col)
        return IfStmt(cond, body, else_body, tok.line, tok.col)

    def parse_for(self):
        tok = self.advance()
        var = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.KW_IN)
        iterable = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = Block(self.parse_block(), tok.line, tok.col)
        return ForStmt(var.value, iterable, body, tok.line, tok.col)

    def parse_while(self):
        tok = self.advance()
        cond = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = Block(self.parse_block(), tok.line, tok.col)
        return WhileStmt(cond, body, tok.line, tok.col)

    def parse_ret(self):
        tok = self.advance()
        if self.peek().type in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF):
            return RetStmt(None, tok.line, tok.col)
        value = self.parse_expr()
        return RetStmt(value, tok.line, tok.col)

    def parse_break(self):
        tok = self.advance()
        return BreakStmt(tok.line, tok.col)

    def parse_continue(self):
        tok = self.advance()
        return ContinueStmt(tok.line, tok.col)

    def parse_import(self):
        tok = self.advance()
        if self.peek().type == TokenType.KW_FROM:
            self.advance()
            module = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.KW_IMPORT)
            names = [self.expect(TokenType.IDENTIFIER).value]
            while self.match(TokenType.COMMA):
                names.append(self.expect(TokenType.IDENTIFIER).value)
            return ImportStmt(module, names, from_module=module, line=tok.line, col=tok.col)
        # Support both `import lib.strings` and `import "lib/strings.zap"`
        if self.peek().type == TokenType.STRING:
            module = self.advance().value
            return ImportStmt(module, None, line=tok.line, col=tok.col)
        module = self.expect(TokenType.IDENTIFIER).value
        names = None
        if self.peek().type == TokenType.COLON and self.peek(1).value == ':':
            self.advance()
            self.advance()
            name = self.expect(TokenType.IDENTIFIER).value
            names = [name]
            while self.match(TokenType.COMMA):
                names.append(self.expect(TokenType.IDENTIFIER).value)
        return ImportStmt(module, names, line=tok.line, col=tok.col)

    def parse_class(self):
        tok = self.advance()
        name = self.expect(TokenType.IDENTIFIER).value
        base = None
        if self.match(TokenType.LPAREN):
            base = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.RPAREN)
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        methods = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_FN:
                fn_def = self.parse_fn_def()
                methods.append(fn_def)
            else:
                break
        while self.peek().type == TokenType.DEDENT:
            d = self.advance()
            if d.value == self._indents[-1]:
                break
            if d.value < self._indents[-1]:
                while self._indents and self._indents[-1] > d.value:
                    self._indents.pop()
                break
        return ClassDef(name, methods, base, tok.line, tok.col)

    def parse_match(self):
        tok = self.advance()
        value = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.skip_newlines()
        indent_tok = self.expect(TokenType.INDENT)
        self._indents.append(indent_tok.value)
        cases = []
        while self.peek().type not in (TokenType.DEDENT, TokenType.EOF):
            if self.peek().type == TokenType.KW_EL:
                self.advance()
                self.expect(TokenType.COLON)
                self.expect(TokenType.NEWLINE)
                body = Block(self.parse_block())
                cases.append(('_', body))
                break
            pattern = self.parse_expr()
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            body = Block(self.parse_block())
            cases.append((pattern, body))
        while self.peek().type == TokenType.DEDENT:
            d = self.advance()
            if d.value == self._indents[-1]:
                break
            if d.value < self._indents[-1]:
                while self._indents and self._indents[-1] > d.value:
                    self._indents.pop()
                break
        return MatchStmt(value, cases, tok.line, tok.col)

    def parse_expr_stmt(self):
        tok = self.peek()
        if tok.type in (TokenType.NUMBER, TokenType.FLOAT) and self.peek(1).type in (TokenType.EQ, TokenType.ASSIGN):
            name_tok = self.advance()
            self.advance()
            value = self.parse_expr()
            return AssignStmt(Identifier(str(name_tok.value)), value, name_tok.line, name_tok.col)
        if tok.type in SYMBOL_TOKENS and self.peek(1).type == TokenType.EQ:
            name_tok = self.advance()
            self.advance()
            value = self.parse_expr()
            return AssignStmt(Identifier(str(name_tok.value)), value, name_tok.line, name_tok.col)
        if tok.type in SYMBOL_TOKENS and self.peek(1).type == TokenType.ASSIGN:
            name_tok = self.advance()
            self.advance()
            value = self.parse_expr()
            return AssignStmt(Identifier(str(name_tok.value)), value, name_tok.line, name_tok.col)
        expr = self.parse_expr()
        if self.peek().type in (TokenType.EQ, TokenType.ASSIGN):
            op = self.advance()
            value = self.parse_expr()
            return AssignStmt(expr, value, expr.line, expr.col)
        if self.peek().type == TokenType.PLUS_ASSIGN:
            self.advance()
            value = self.parse_expr()
            return AugAssignStmt(expr, '+=', value, expr.line, expr.col)
        if self.peek().type == TokenType.MINUS_ASSIGN:
            self.advance()
            value = self.parse_expr()
            return AugAssignStmt(expr, '-=', value, expr.line, expr.col)
        return ExprStmt(expr, expr.line, expr.col)

    def parse_expr(self):
        return self.parse_pipe()

    def parse_pipe(self):
        left = self.parse_or()
        while self.match(TokenType.PIPE):
            right = self.parse_or()
            left = BinOp(left, '|>', right, left.line, left.col)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.peek().type in (TokenType.KW_OR, TokenType.OR):
            op = self.advance()
            right = self.parse_and()
            left = BinOp(left, 'or', right, left.line, left.col)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek().type in (TokenType.KW_AND, TokenType.AND):
            op = self.advance()
            right = self.parse_not()
            left = BinOp(left, 'and', right, left.line, left.col)
        return left

    def parse_not(self):
        if self.peek().type in (TokenType.KW_NOT, TokenType.NOT):
            op = self.advance()
            return UnaryOp('not', self.parse_not(), op.line, op.col)
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_addition()
        while self.peek().type in (TokenType.EQEQ, TokenType.NEQ, TokenType.LT,
                                   TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance()
            right = self.parse_addition()
            left = BinOp(left, op.value, right, left.line, left.col)
        return left

    def parse_addition(self):
        left = self.parse_multiplication()
        while self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self.parse_multiplication()
            left = BinOp(left, op.value, right, left.line, left.col)
        return left

    def parse_multiplication(self):
        left = self.parse_unary()
        while self.peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, TokenType.MATMUL):
            op = self.advance()
            right = self.parse_unary()
            left = BinOp(left, op.value, right, left.line, left.col)
        return left

    def parse_unary(self):
        if self.peek().type in (TokenType.MINUS, TokenType.PLUS):
            next_tok = self.peek(1)
            if next_tok.type in (TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF,
                                 TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE,
                                 TokenType.COMMA, TokenType.COLON, TokenType.EQ):
                tok = self.advance()
                return Identifier(str(tok.value), tok.line, tok.col)
            op = self.advance()
            return UnaryOp(op.value, self.parse_unary(), op.line, op.col)
        return self.parse_power()

    def parse_power(self):
        left = self.parse_call()
        if self.match(TokenType.POW):
            right = self.parse_unary()
            left = BinOp(left, '**', right, left.line, left.col)
        return left

    def parse_call(self):
        left = self.parse_primary()
        while True:
            if self.match(TokenType.LPAREN):
                args = []
                if self.peek().type != TokenType.RPAREN:
                    args.append(self.parse_expr())
                    while self.match(TokenType.COMMA):
                        if self.peek().type == TokenType.RPAREN:
                            break
                        args.append(self.parse_expr())
                self.expect(TokenType.RPAREN)
                left = Call(left, args, left.line, left.col)
            elif self.match(TokenType.LBRACKET):
                if self.peek().type == TokenType.COLON:
                    self.advance()
                    stop = None
                    step = None
                    if self.peek().type == TokenType.COLON:
                        self.advance()
                        step = self.parse_expr() if self.peek().type != TokenType.RBRACKET else None
                    elif self.peek().type != TokenType.RBRACKET:
                        stop = self.parse_expr()
                        if self.match(TokenType.COLON):
                            step = self.parse_expr() if self.peek().type != TokenType.RBRACKET else None
                    self.expect(TokenType.RBRACKET)
                    left = Slice(left, None, stop, step, left.line, left.col)
                else:
                    index = self.parse_expr()
                    if self.match(TokenType.COLON):
                        stop = None
                        step = None
                        if self.peek().type != TokenType.RBRACKET:
                            stop = self.parse_expr()
                        if self.match(TokenType.COLON):
                            step = self.parse_expr() if self.peek().type != TokenType.RBRACKET else None
                        self.expect(TokenType.RBRACKET)
                        left = Slice(left, index, stop, step, left.line, left.col)
                    else:
                        self.expect(TokenType.RBRACKET)
                        left = Index(left, index, left.line, left.col)
            elif self.match(TokenType.DOT):
                member = self.expect(TokenType.IDENTIFIER)
                left = MemberAccess(left, member.value, left.line, left.col)
            else:
                break
        return left

    def parse_primary(self):
        tok = self.advance()

        if tok.type == TokenType.NUMBER:
            return Literal(tok.value, tok.line, tok.col)
        if tok.type == TokenType.FLOAT:
            return Literal(tok.value, tok.line, tok.col)
        if tok.type == TokenType.STRING:
            return Literal(tok.value, tok.line, tok.col)
        if tok.type == TokenType.KW_TRUE:
            return Literal(True, tok.line, tok.col)
        if tok.type == TokenType.KW_FALSE:
            return Literal(False, tok.line, tok.col)
        if tok.type == TokenType.KW_NONE:
            return Literal(None, tok.line, tok.col)

        if tok.type in (TokenType.IDENTIFIER, TokenType.KW_VERSION, TokenType.KW_REQUIRES, TokenType.KW_ENSURES):
            if self.peek().type == TokenType.ARROW:
                params = [{'name': tok.value}]
                self.advance()
                body = self.parse_expr()
                return Lambda(params, body, tok.line, tok.col)
            return Identifier(tok.value, tok.line, tok.col)

        if tok.type == TokenType.LPAREN:
            if self.peek().type == TokenType.RPAREN:
                self.advance()
                if self.peek().type == TokenType.ARROW:
                    self.advance()
                    body = self.parse_expr()
                    return Lambda([], body, tok.line, tok.col)
                self.error("empty parentheses must be a lambda: () => ...")
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN)
            return expr

        if tok.type == TokenType.LBRACKET:
            elements = []
            if self.peek().type != TokenType.RBRACKET:
                first = self.parse_expr()
                # Check for list comprehension: [expr for item in iterable]
                if self.peek().type == TokenType.KW_FOR:
                    bindings = []
                    while self.peek().type == TokenType.KW_FOR:
                        self.advance()  # consume 'for'
                        var = self.expect(TokenType.IDENTIFIER).value
                        self.expect(TokenType.KW_IN)
                        iterable = self.parse_expr()
                        bindings.append((var, iterable))
                    condition = None
                    if self.peek().type == TokenType.KW_IF:
                        self.advance()
                        condition = self.parse_expr()
                    self.expect(TokenType.RBRACKET)
                    return ListComprehension(first, bindings, condition, tok.line, tok.col)
                elements.append(first)
                while self.match(TokenType.COMMA):
                    if self.peek().type == TokenType.RBRACKET:
                        break
                    elements.append(self.parse_expr())
            self.expect(TokenType.RBRACKET)
            return ListLiteral(elements, tok.line, tok.col)

        if tok.type == TokenType.LBRACE:
            entries = []
            if self.peek().type != TokenType.RBRACE:
                # Parse first key-value pair (or dict comprehension)
                key_expr = self.parse_expr()
                if self.peek().type == TokenType.COLON:
                    self.advance()  # consume ':'
                    value_expr = self.parse_expr()
                    if self.peek().type == TokenType.KW_FOR:
                        bindings = []
                        while self.peek().type == TokenType.KW_FOR:
                            self.advance()  # consume 'for'
                            var = self.expect(TokenType.IDENTIFIER).value
                            self.expect(TokenType.KW_IN)
                            iterable = self.parse_expr()
                            bindings.append((var, iterable))
                        condition = None
                        if self.peek().type == TokenType.KW_IF:
                            self.advance()
                            condition = self.parse_expr()
                        self.expect(TokenType.RBRACE)
                        return DictComprehension(key_expr, value_expr, bindings, condition, tok.line, tok.col)
                    entries.append((key_expr, value_expr))
                    while self.match(TokenType.COMMA):
                        if self.peek().type == TokenType.RBRACE:
                            break
                        key = self.parse_expr()
                        self.expect(TokenType.COLON)
                        value = self.parse_expr()
                        entries.append((key, value))
            self.expect(TokenType.RBRACE)
            return DictLiteral(entries, tok.line, tok.col)

        if tok.type == TokenType.MINUS:
            return UnaryOp('-', self.parse_unary(), tok.line, tok.col)

        if tok.type in SYMBOL_TOKENS:
            return Identifier(str(tok.value), tok.line, tok.col)

        # Keywords can be used as identifiers in expression context (e.g. dict keys)
        if tok.type.name.startswith('KW_'):
            return Identifier(tok.value, tok.line, tok.col)

        self.error(f"unexpected token: {tok.type.name} ('{tok.value}')")
