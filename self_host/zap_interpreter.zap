// zap_interpreter.zap — Full Zap interpreter written in Zap
// This is a self-hosting Zap interpreter: parses and executes Zap code
// Usage: zap run zap_interpreter.zap <script.zap>

let args = sys_args()
if len(args) < 2 {
    print("Usage: zap run zap_interpreter.zap <script.zap>")
    print("  or:  zap run zap_interpreter.zap --repl")
    sys_exit(1)
}

let script_file = args[1]

if script_file == "--repl" {
    run_repl()
} else {
    let source = read_file(script_file)
    let result = execute(source, script_file)
    if result != none {
        print(result)
    }
}

// ---- Main Execution ----

fn execute(source, filename) {
    let tokens = tokenize(source, filename)
    let ast = parse(tokens)
    let env = create_global_env()
    return eval_program(ast, env)
}

// ---- Integration with Zap CLI ----

fn run_interpreter(script_file) {
    let source = read_file(script_file)
    let result = execute(source, script_file)
    if result != none {
        print(result)
    }
}

// ---- REPL ----

fn run_repl() {
    print("Zap REPL (self-hosted)")
    print("Type 'exit' to quit")
    
    let env = create_global_env()
    
    loop {
        let line = input(">>> ")
        if line == "exit" {
            break
        }
        if line == "" {
            continue
        }
        let result = execute(line, "<repl>")
        if result != none {
            print("= " + str(result))
        }
    }
}

// ---- Tokenizer ----

fn tokenize(source, filename) {
    let tokens = []
    let i = 0
    let line = 1
    let col = 1
    
    while i < len(source) {
        let ch = source[i]
        let ch2 = ""
        if i + 1 < len(source) {
            ch2 = source[i + 1]
        }
        
        // Skip whitespace (but track newlines)
        if ch == "\n" {
            line = line + 1
            col = 1
            i = i + 1
            continue
        }
        if ch == " " || ch == "\t" || ch == "\r" {
            col = col + 1
            i = i + 1
            continue
        }
        
        // Skip comments
        if ch == "/" && ch2 == "/" {
            while i < len(source) && source[i] != "\n" {
                i = i + 1
            }
            continue
        }
        
        // Numbers
        if (ch >= "0" && ch <= "9") || (ch == "." && ch2 >= "0" && ch2 <= "9") {
            let num_str = ""
            let is_float = false
            while i < len(source) && ((source[i] >= "0" && source[i] <= "9") || source[i] == ".") {
                if source[i] == "." {
                    is_float = true
                }
                num_str = num_str + source[i]
                i = i + 1
            }
            if is_float {
                tokens.append({"type": "FLOAT", "value": float(num_str), "line": line, "col": col})
            } else {
                tokens.append({"type": "NUMBER", "value": int(num_str), "line": line, "col": col})
            }
            col = col + len(num_str)
            continue
        }
        
        // Strings
        if ch == '"' || ch == "'" {
            let quote = ch
            let str_val = ""
            i = i + 1
            while i < len(source) && source[i] != quote {
                if source[i] == "\\" && i + 1 < len(source) {
                    i = i + 1
                    if source[i] == "n" {
                        str_val = str_val + "\n"
                    } else if source[i] == "t" {
                        str_val = str_val + "\t"
                    } else if source[i] == "\\" {
                        str_val = str_val + "\\"
                    } else if source[i] == quote {
                        str_val = str_val + quote
                    } else {
                        str_val = str_val + source[i]
                    }
                } else {
                    str_val = str_val + source[i]
                }
                i = i + 1
            }
            i = i + 1  // skip closing quote
            tokens.append({"type": "STRING", "value": str_val, "line": line, "col": col})
            col = col + len(str_val) + 2
            continue
        }
        
        // Identifiers and keywords
        if is_alpha(ch) {
            let ident = ""
            while i < len(source) && is_alnum(source[i]) {
                ident = ident + source[i]
                i = i + 1
            }
            
            let token_type = get_keyword_type(ident)
            if token_type != "IDENTIFIER" {
                tokens.append({"type": token_type, "value": ident, "line": line, "col": col})
            } else {
                tokens.append({"type": "IDENTIFIER", "value": ident, "line": line, "col": col})
            }
            col = col + len(ident)
            continue
        }
        
        // Symbols and operators
        let sym = ch
        i = i + 1
        col = col + 1
        
        // Multi-character operators
        if ch == "=" && ch2 == "=" {
            sym = "=="
            i = i + 1
            col = col + 1
        } else if ch == "!" && ch2 == "=" {
            sym = "!="
            i = i + 1
            col = col + 1
        } else if ch == "<" && ch2 == "=" {
            sym = "<="
            i = i + 1
            col = col + 1
        } else if ch == ">" && ch2 == "=" {
            sym = ">="
            i = i + 1
            col = col + 1
        } else if ch == "&" && ch2 == "&" {
            sym = "&&"
            i = i + 1
            col = col + 1
        } else if ch == "|" && ch2 == "|" {
            sym = "||"
            i = i + 1
            col = col + 1
        } else if ch == "+" && ch2 == "=" {
            sym = "+="
            i = i + 1
            col = col + 1
        } else if ch == "-" && ch2 == "=" {
            sym = "-="
            i = i + 1
            col = col + 1
        } else if ch == "*" && ch2 == "=" {
            sym = "*="
            i = i + 1
            col = col + 1
        } else if ch == "/" && ch2 == "=" {
            sym = "/="
            i = i + 1
            col = col + 1
        } else if ch == "-" && ch2 == ">" {
            sym = "->"
            i = i + 1
            col = col + 1
        }
        
        let token = {"type": get_symbol_type(sym), "value": sym, "line": line, "col": col}
        tokens.append(token)
    }
    
    tokens.append({"type": "EOF", "value": none, "line": line, "col": col})
    return tokens
}

fn get_keyword_type(word) {
    if word == "let" { return "LET" }
    if word == "fn" { return "FN" }
    if word == "if" { return "IF" }
    if word == "else" { return "ELSE" }
    if word == "while" { return "WHILE" }
    if word == "for" { return "FOR" }
    if word == "in" { return "IN" }
    if word == "return" { return "RETURN" }
    if word == "break" { return "BREAK" }
    if word == "continue" { return "CONTINUE" }
    if word == "true" { return "TRUE" }
    if word == "false" { return "FALSE" }
    if word == "none" { return "NONE" }
    if word == "and" { return "AND" }
    if word == "or" { return "OR" }
    if word == "not" { return "NOT" }
    return "IDENTIFIER"
}

fn get_symbol_type(sym) {
    if sym == "(" { return "LPAREN" }
    if sym == ")" { return "RPAREN" }
    if sym == "{" { return "LBRACE" }
    if sym == "}" { return "RBRACE" }
    if sym == "[" { return "LBRACKET" }
    if sym == "]" { return "RBRACKET" }
    if sym == "," { return "COMMA" }
    if sym == "." { return "DOT" }
    if sym == ":" { return "COLON" }
    if sym == "=" { return "ASSIGN" }
    if sym == "+" { return "PLUS" }
    if sym == "-" { return "MINUS" }
    if sym == "*" { return "STAR" }
    if sym == "/" { return "SLASH" }
    if sym == "%" { return "PERCENT" }
    if sym == "!" { return "BANG" }
    if sym == "<" { return "LT" }
    if sym == ">" { return "GT" }
    if sym == "-" { return "MINUS" }
    if sym == "==" { return "EQ" }
    if sym == "!=" { return "NEQ" }
    if sym == "<=" { return "LTE" }
    if sym == ">=" { return "GTE" }
    if sym == "&&" { return "AND" }
    if sym == "||" { return "OR" }
    if sym == "+=" { return "PLUS_ASSIGN" }
    if sym == "-=" { return "MINUS_ASSIGN" }
    if sym == "*=" { return "STAR_ASSIGN" }
    if sym == "/=" { return "SLASH_ASSIGN" }
    if sym == "->" { return "ARROW" }
    return "SYMBOL"
}

// ---- Parser ----

fn parse(tokens) {
    let stmts = []
    let pos = 0
    
    while pos < len(tokens) {
        let tok = tokens[pos]
        if tok.typ == "EOF" {
            break
        }
        
        let stmt = parse_stmt(tokens, pos)
        stmts.append(stmt.node)
        pos = stmt.pos
    }
    
    return {"type": "Program", "stmts": stmts}
}

fn parse_stmt(tokens, pos) {
    let tok = tokens[pos]
    
    if tok.typ == "LET" {
        return parse_let(tokens, pos)
    }
    if tok.typ == "FN" {
        return parse_fn(tokens, pos)
    }
    if tok.typ == "IF" {
        return parse_if(tokens, pos)
    }
    if tok.typ == "WHILE" {
        return parse_while(tokens, pos)
    }
    if tok.typ == "FOR" {
        return parse_for(tokens, pos)
    }
    if tok.typ == "RETURN" {
        return parse_return(tokens, pos)
    }
    if tok.typ == "BREAK" {
        return {"node": {"type": "Break"}, "pos": pos + 1}
    }
    if tok.typ == "CONTINUE" {
        return {"node": {"type": "Continue"}, "pos": pos + 1}
    }
    
    // Expression statement
    let result = parse_expr(tokens, pos)
    return {"node": {"type": "ExprStmt", "expr": result.node}, "pos": result.pos}
}

fn parse_let(tokens, pos) {
    pos = pos + 1  // skip 'let'
    let name = tokens[pos].value
    pos = pos + 1  // skip identifier
    
    if tokens[pos].type == "ASSIGN" {
        pos = pos + 1  // skip '='
        let result = parse_expr(tokens, pos)
        return {"node": {"type": "Let", "name": name, "value": result.node}, "pos": result.pos}
    }
    
    return {"node": {"type": "Let", "name": name, "value": none}, "pos": pos}
}

fn parse_fn(tokens, pos) {
    pos = pos + 1  // skip 'fn'
    let name = tokens[pos].value
    pos = pos + 1  // skip name
    
    // Parse params
    pos = pos + 1  // skip '('
    let params = []
    while tokens[pos].type != "RPAREN" {
        params.append(tokens[pos].value)
        pos = pos + 1
        if tokens[pos].type == "COMMA" {
            pos = pos + 1
        }
    }
    pos = pos + 1  // skip ')'
    
    // Parse body
    pos = pos + 1  // skip '{'
    let body = []
    while tokens[pos].type != "RBRACE" {
        let result = parse_stmt(tokens, pos)
        body.append(result.node)
        pos = result.pos
    }
    pos = pos + 1  // skip '}'
    
    return {"node": {"type": "Fn", "name": name, "params": params, "body": body}, "pos": pos}
}

fn parse_if(tokens, pos) {
    pos = pos + 1  // skip 'if'
    let result = parse_expr(tokens, pos)
    let condition = result.node
    pos = result.pos
    
    pos = pos + 1  // skip '{'
    let body = []
    while tokens[pos].type != "RBRACE" {
        let stmt = parse_stmt(tokens, pos)
        body.append(stmt.node)
        pos = stmt.pos
    }
    pos = pos + 1  // skip '}'
    
    let else_body = none
    if pos < len(tokens) && tokens[pos].type == "ELSE" {
        pos = pos + 1  // skip 'else'
        if pos < len(tokens) && tokens[pos].type == "IF" {
            let else_if = parse_if(tokens, pos)
            else_body = [else_if.node]
            pos = else_if.pos
        } else {
            pos = pos + 1  // skip '{'
            else_body = []
            while tokens[pos].type != "RBRACE" {
                let stmt = parse_stmt(tokens, pos)
                else_body.append(stmt.node)
                pos = stmt.pos
            }
            pos = pos + 1  // skip '}'
        }
    }
    
    return {"node": {"type": "If", "condition": condition, "body": body, "else_body": else_body}, "pos": pos}
}

fn parse_while(tokens, pos) {
    pos = pos + 1  // skip 'while'
    let result = parse_expr(tokens, pos)
    let condition = result.node
    pos = result.pos
    
    pos = pos + 1  // skip '{'
    let body = []
    while tokens[pos].type != "RBRACE" {
        let stmt = parse_stmt(tokens, pos)
        body.append(stmt.node)
        pos = stmt.pos
    }
    pos = pos + 1  // skip '}'
    
    return {"node": {"type": "While", "condition": condition, "body": body}, "pos": pos}
}

fn parse_for(tokens, pos) {
    pos = pos + 1  // skip 'for'
    let var_name = tokens[pos].value
    pos = pos + 1  // skip variable
    pos = pos + 1  // skip 'in'
    let result = parse_expr(tokens, pos)
    let iterable = result.node
    pos = result.pos
    
    pos = pos + 1  // skip '{'
    let body = []
    while tokens[pos].type != "RBRACE" {
        let stmt = parse_stmt(tokens, pos)
        body.append(stmt.node)
        pos = stmt.pos
    }
    pos = pos + 1  // skip '}'
    
    return {"node": {"type": "For", "var": var_name, "iterable": iterable, "body": body}, "pos": pos}
}

fn parse_return(tokens, pos) {
    pos = pos + 1  // skip 'return'
    let value = none
    if pos < len(tokens) && tokens[pos].type != "RBRACE" {
        let result = parse_expr(tokens, pos)
        value = result.node
        pos = result.pos
    }
    return {"node": {"type": "Return", "value": value}, "pos": pos}
}

// ---- Expression Parser (Pratt parser) ----

fn parse_expr(tokens, pos) {
    return parse_comparison(tokens, pos)
}

fn parse_comparison(tokens, pos) {
    let left = parse_addition(tokens, pos)
    
    while left.pos < len(tokens) {
        let tok = tokens[left.pos]
        if tok.typ == "EQ" || tok.typ == "NEQ" || tok.typ == "LT" || tok.typ == "GT" || tok.typ == "LTE" || tok.typ == "GTE" {
            let right = parse_addition(tokens, left.pos + 1)
            left = {"node": {"type": "BinOp", "op": tok.value, "left": left.node, "right": right.node}, "pos": right.pos}
        } else {
            break
        }
    }
    
    return left
}

fn parse_addition(tokens, pos) {
    let left = parse_multiplication(tokens, pos)
    
    while left.pos < len(tokens) {
        let tok = tokens[left.pos]
        if tok.typ == "PLUS" || tok.typ == "MINUS" {
            let right = parse_multiplication(tokens, left.pos + 1)
            left = {"node": {"type": "BinOp", "op": tok.value, "left": left.node, "right": right.node}, "pos": right.pos}
        } else {
            break
        }
    }
    
    return left
}

fn parse_multiplication(tokens, pos) {
    let left = parse_unary(tokens, pos)
    
    while left.pos < len(tokens) {
        let tok = tokens[left.pos]
        if tok.typ == "STAR" || tok.typ == "SLASH" || tok.typ == "PERCENT" {
            let right = parse_unary(tokens, left.pos + 1)
            left = {"node": {"type": "BinOp", "op": tok.value, "left": left.node, "right": right.node}, "pos": right.pos}
        } else {
            break
        }
    }
    
    return left
}

fn parse_unary(tokens, pos) {
    let tok = tokens[pos]
    
    if tok.typ == "MINUS" {
        let result = parse_primary(tokens, pos + 1)
        return {"node": {"type": "UnaryOp", "op": "-", "operand": result.node}, "pos": result.pos}
    }
    if tok.typ == "NOT" {
        let result = parse_primary(tokens, pos + 1)
        return {"node": {"type": "UnaryOp", "op": "not", "operand": result.node}, "pos": result.pos}
    }
    
    return parse_primary(tokens, pos)
}

fn parse_primary(tokens, pos) {
    let tok = tokens[pos]
    
    // Literals
    if tok.typ == "NUMBER" {
        return {"node": {"type": "Number", "value": tok.value}, "pos": pos + 1}
    }
    if tok.typ == "FLOAT" {
        return {"node": {"type": "Float", "value": tok.value}, "pos": pos + 1}
    }
    if tok.typ == "STRING" {
        return {"node": {"type": "String", "value": tok.value}, "pos": pos + 1}
    }
    if tok.typ == "TRUE" {
        return {"node": {"type": "Boolean", "value": true}, "pos": pos + 1}
    }
    if tok.typ == "FALSE" {
        return {"node": {"type": "Boolean", "value": false}, "pos": pos + 1}
    }
    if tok.typ == "NONE" {
        return {"node": {"type": "None"}, "pos": pos + 1}
    }
    
    // Identifier or function call
    if tok.typ == "IDENTIFIER" {
        // Check for function call
        if pos + 1 < len(tokens) && tokens[pos + 1].type == "LPAREN" {
            return parse_call(tokens, pos)
        }
        return {"node": {"type": "Identifier", "name": tok.value}, "pos": pos + 1}
    }
    
    // Parenthesized expression
    if tok.typ == "LPAREN" {
        let result = parse_expr(tokens, pos + 1)
        return {"node": result.node, "pos": result.pos + 1}  // skip ')'
    }
    
    // List literal
    if tok.typ == "LBRACKET" {
        return parse_list(tokens, pos)
    }
    
    // Dict literal
    if tok.typ == "LBRACE" {
        return parse_dict(tokens, pos)
    }
    
    return {"node": {"type": "None"}, "pos": pos + 1}
}

fn parse_call(tokens, pos) {
    let name = tokens[pos].value
    pos = pos + 1  // skip name
    pos = pos + 1  // skip '('
    
    let args = []
    if tokens[pos].type != "RPAREN" {
        let result = parse_expr(tokens, pos)
        args.append(result.node)
        pos = result.pos
        
        while pos < len(tokens) && tokens[pos].type == "COMMA" {
            pos = pos + 1
            result = parse_expr(tokens, pos)
            args.append(result.node)
            pos = result.pos
        }
    }
    pos = pos + 1  // skip ')'
    
    // Check for method call (dot notation)
    while pos < len(tokens) && tokens[pos].type == "DOT" {
        pos = pos + 1  // skip '.'
        let method = tokens[pos].value
        pos = pos + 1  // skip method name
        
        if pos < len(tokens) && tokens[pos].type == "LPAREN" {
            pos = pos + 1  // skip '('
            let method_args = [{"type": "CallResult", "expr": {"type": "Call", "name": name, "args": args}}]
            
            if tokens[pos].type != "RPAREN" {
                let result = parse_expr(tokens, pos)
                method_args.append(result.node)
                pos = result.pos
                
                while pos < len(tokens) && tokens[pos].type == "COMMA" {
                    pos = pos + 1
                    result = parse_expr(tokens, pos)
                    method_args.append(result.node)
                    pos = result.pos
                }
            }
            pos = pos + 1  // skip ')'
            
            name = "method_call"
            args = method_args
        } else {
            // Property access
            name = "property_access"
            args = [{"type": "CallResult", "expr": {"type": "Call", "name": name, "args": args}}, {"type": "String", "value": method}]
        }
    }
    
    return {"node": {"type": "Call", "name": name, "args": args}, "pos": pos}
}

fn parse_list(tokens, pos) {
    pos = pos + 1  // skip '['
    let elements = []
    
    if tokens[pos].type != "RBRACKET" {
        let result = parse_expr(tokens, pos)
        elements.append(result.node)
        pos = result.pos
        
        while pos < len(tokens) && tokens[pos].type == "COMMA" {
            pos = pos + 1
            result = parse_expr(tokens, pos)
            elements.append(result.node)
            pos = result.pos
        }
    }
    pos = pos + 1  // skip ']'
    
    return {"node": {"type": "List", "elements": elements}, "pos": pos}
}

fn parse_dict(tokens, pos) {
    pos = pos + 1  // skip '{'
    let entries = []
    
    if tokens[pos].type != "RBRACE" {
        let key = parse_expr(tokens, pos)
        pos = key.pos
        pos = pos + 1  // skip ':'
        let value = parse_expr(tokens, pos)
        entries.append({"key": key.node, "value": value.node})
        pos = value.pos
        
        while pos < len(tokens) && tokens[pos].type == "COMMA" {
            pos = pos + 1
            key = parse_expr(tokens, pos)
            pos = key.pos
            pos = pos + 1  // skip ':'
            value = parse_expr(tokens, pos)
            entries.append({"key": key.node, "value": value.node})
            pos = value.pos
        }
    }
    pos = pos + 1  // skip '}'
    
    return {"node": {"type": "Dict", "entries": entries}, "pos": pos}
}

// ---- Evaluator ----

fn create_global_env() {
    let env = {
        "variables": {},
        "parent": none
    }
    
    // Built-in functions
    env.variables["print"] = {"type": "builtin", "fn": builtin_print}
    env.variables["len"] = {"type": "builtin", "fn": builtin_len}
    env.variables["str"] = {"type": "builtin", "fn": builtin_str}
    env.variables["int"] = {"type": "builtin", "fn": builtin_int}
    env.variables["float"] = {"type": "builtin", "fn": builtin_float}
    env.variables["input"] = {"type": "builtin", "fn": builtin_input}
    env.variables["type"] = {"type": "builtin", "fn": builtin_type}
    env.variables["append"] = {"type": "builtin", "fn": builtin_append}
    env.variables["range"] = {"type": "builtin", "fn": builtin_range}
    env.variables["read_file"] = {"type": "builtin", "fn": builtin_read_file}
    env.variables["write_file"] = {"type": "builtin", "fn": builtin_write_file}
    env.variables["sys_args"] = {"type": "builtin", "fn": builtin_sys_args}
    env.variables["sys_exit"] = {"type": "builtin", "fn": builtin_sys_exit}
    env.variables["math"] = {"type": "module", "values": {
        "pi": 3.14159265358979,
        "e": 2.71828182845905
    }}
    
    return env
}

fn eval_program(ast, env) {
    let result = none
    for stmt in ast.stmts {
        result = eval_stmt(stmt, env)
        if type(result) == "return" {
            return result.value
        }
        if type(result) == "break" || type(result) == "continue" {
            break
        }
    }
    return result
}

fn eval_stmt(stmt, env) {
    if stmt.typ == "Let" {
        let value = eval_expr(stmt.value, env)
        env.variables[stmt.name] = value
        return none
    }
    
    if stmt.typ == "Fn" {
        env.variables[stmt.name] = {"type": "function", "params": stmt.params, "body": stmt.body, "env": env}
        return none
    }
    
    if stmt.typ == "If" {
        let condition = eval_expr(stmt.condition, env)
        if is_truthy(condition) {
            let result = none
            for body_stmt in stmt.body {
                result = eval_stmt(body_stmt, env)
                if type(result) == "return" || type(result) == "break" || type(result) == "continue" {
                    return result
                }
            }
            return result
        } else if stmt.else_body != none {
            let result = none
            for body_stmt in stmt.else_body {
                result = eval_stmt(body_stmt, env)
                if type(result) == "return" || type(result) == "break" || type(result) == "continue" {
                    return result
                }
            }
            return result
        }
        return none
    }
    
    if stmt.typ == "While" {
        while is_truthy(eval_expr(stmt.condition, env)) {
            let result = none
            for body_stmt in stmt.body {
                result = eval_stmt(body_stmt, env)
                if type(result) == "return" {
                    return result
                }
                if type(result) == "break" {
                    return none
                }
                if type(result) == "continue" {
                    break
                }
            }
        }
        return none
    }
    
    if stmt.typ == "For" {
        let iterable = eval_expr(stmt.iterable, env)
        for item in iterable {
            env.variables[stmt.var] = item
            let result = none
            for body_stmt in stmt.body {
                result = eval_stmt(body_stmt, env)
                if type(result) == "return" {
                    return result
                }
                if type(result) == "break" {
                    return none
                }
                if type(result) == "continue" {
                    break
                }
            }
        }
        return none
    }
    
    if stmt.typ == "Return" {
        let value = none
        if stmt.value != none {
            value = eval_expr(stmt.value, env)
        }
        return {"type": "return", "value": value}
    }
    
    if stmt.typ == "Break" {
        return {"type": "break"}
    }
    
    if stmt.typ == "Continue" {
        return {"type": "continue"}
    }
    
    if stmt.typ == "ExprStmt" {
        return eval_expr(stmt.expr, env)
    }
    
    return none
}

fn eval_expr(expr, env) {
    if expr.typ == "Number" {
        return expr.value
    }
    if expr.typ == "Float" {
        return expr.value
    }
    if expr.typ == "String" {
        return expr.value
    }
    if expr.typ == "Boolean" {
        return expr.value
    }
    if expr.typ == "None" {
        return none
    }
    
    if expr.typ == "Identifier" {
        return lookup_var(expr.name, env)
    }
    
    if expr.typ == "BinOp" {
        let left = eval_expr(expr.left, env)
        let right = eval_expr(expr.right, env)
        return eval_binop(expr.op, left, right)
    }
    
    if expr.typ == "UnaryOp" {
        let operand = eval_expr(expr.operand, env)
        if expr.op == "-" {
            return -operand
        }
        if expr.op == "not" {
            return not is_truthy(operand)
        }
    }
    
    if expr.typ == "Call" {
        let callee = lookup_var(expr.name, env)
        let args = []
        for arg in expr.args {
            args.append(eval_expr(arg, env))
        }
        return call_function(callee, args, env)
    }
    
    if expr.typ == "List" {
        let elements = []
        for elem in expr.elements {
            elements.append(eval_expr(elem, env))
        }
        return elements
    }
    
    if expr.typ == "Dict" {
        let entries = {}
        for entry in expr.entries {
            let key = eval_expr(entry.key, env)
            let value = eval_expr(entry.value, env)
            entries[str(key)] = value
        }
        return entries
    }
    
    return none
}

fn eval_binop(op, left, right) {
    if op == "+" { return left + right }
    if op == "-" { return left - right }
    if op == "*" { return left * right }
    if op == "/" { return left / right }
    if op == "%" { return left % right }
    if op == "==" { return left == right }
    if op == "!=" { return left != right }
    if op == "<" { return left < right }
    if op == ">" { return left > right }
    if op == "<=" { return left <= right }
    if op == ">=" { return left >= right }
    if op == "&&" { return is_truthy(left) && is_truthy(right) }
    if op == "||" { return is_truthy(left) || is_truthy(right) }
    return none
}

fn is_truthy(val) {
    if val == none { return false }
    if val == false { return false }
    if val == 0 { return false }
    if val == "" { return false }
    return true
}

fn lookup_var(name, env) {
    if name in env.variables {
        return env.variables[name]
    }
    if env.parent != none {
        return lookup_var(name, env.parent)
    }
    print("Error: undefined variable '$name'")
    return none
}

fn call_function(callee, args, env) {
    if callee.typ == "builtin" {
        return callee.fn(args)
    }
    
    if callee.typ == "function" {
        let child_env = {"variables": {}, "parent": callee.env}
        for i in range(len(callee.params)) {
            child_env.variables[callee.params[i]] = args[i]
        }
        
        let result = none
        for stmt in callee.body {
            result = eval_stmt(stmt, child_env)
            if type(result) == "return" {
                return result.value
            }
        }
        return result
    }
    
    print("Error: not callable")
    return none
}

// ---- Built-in Functions ----

fn builtin_print(args) {
    let parts = []
    for arg in args {
        parts.append(str(arg))
    }
    print(parts.join(" "))
    return none
}

fn builtin_len(args) {
    let obj = args[0]
    if type(obj) == "string" {
        let count = 0
        for ch in obj {
            count = count + 1
        }
        return count
    }
    if type(obj) == "list" {
        let count = 0
        for item in obj {
            count = count + 1
        }
        return count
    }
    return 0
}

fn builtin_str(args) {
    return str(args[0])
}

fn builtin_int(args) {
    return int(args[0])
}

fn builtin_float(args) {
    return float(args[0])
}

fn builtin_input(args) {
    return input(args[0])
}

fn builtin_type(args) {
    return type(args[0])
}

fn builtin_append(args) {
    let list = args[0]
    let item = args[1]
    list.append(item)
    return none
}

fn builtin_range(args) {
    let end = args[0]
    let result = []
    let i = 0
    while i < end {
        result.append(i)
        i = i + 1
    }
    return result
}

fn builtin_read_file(args) {
    return read_file(args[0])
}

fn builtin_write_file(args) {
    write_file(args[0], args[1])
    return none
}

fn builtin_sys_args() {
    return sys_args()
}

fn builtin_sys_exit(args) {
    sys_exit(args[0])
    return none
}

// ---- Helpers ----

fn is_alpha(ch) {
    return (ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z") || ch == "_"
}

fn is_alnum(ch) {
    return is_alpha(ch) || (ch >= "0" && ch <= "9")
}
