const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const BUILTINS = {
  functions: {
    io: ['print', 'say', 'show', 'ask', 'read_file', 'write_file', 'append_file', 'read_line', 'read_all', 'file_exists', 'list_dir', 'mkdir', 'remove', 'file_size'],
    string: ['upper', 'lower', 'strip', 'split', 'join', 'replace', 'startswith', 'endswith', 'contains', 'find', 'reverse', 'trim', 'format', 'capitalize', 'title', 'rfind', 'rindex', 'count'],
    collection: ['len', 'map', 'filter', 'sort', 'reversed', 'zip', 'enumerate', 'flatten', 'chunk', 'unique', 'any', 'all', 'sum', 'first', 'last', 'take', 'drop', 'group_by', 'partition', 'index', 'append', 'extend', 'pop', 'remove', 'clear', 'insert'],
    math: ['abs', 'max', 'min', 'round', 'floor', 'ceil', 'sqrt', 'pow', 'exp', 'log', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'pi', 'e', 'random', 'randint', 'seed', 'gcd', 'lcm', 'factorial'],
    type: ['type', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple', 'range', 'isinstance', 'getattr', 'hasattr', 'setattr', 'callable'],
    async: ['par_map', 'par_filter', 'par_for', 'pmap', 'parallel', 'spawn', 'await', 'yield', 'channel', 'send', 'recv', 'select', 'sleep'],
    io: ['json_parse', 'json_stringify', 'json_load', 'json_save', 'csv_load', 'csv_save', 'http_get', 'http_post', 'http_put', 'http_delete', 'http_patch', 'web_fetch', 'download', 'image_load', 'image_save'],
    db: ['db_open', 'db_query', 'db_query_one', 'db_exec', 'db_transaction', 'db_migrate', 'db_tables', 'db_schema', 'db_close'],
    ml: ['tensor', 'zeros', 'ones', 'reshape', 'dense', 'conv2d', 'batch_norm', 'dropout', 'relu', 'sigmoid', 'tanh', 'softmax', 'leaky_relu', 'elu', 'mse_loss', 'cross_entropy_loss', 'model', 'train', 'predict', 'save_model', 'load_model', 'model_summary', 'normalize', 'split_data', 'batch', 'one_hot', 'argmax', 'accuracy', 'seed'],
    system: ['env_get', 'env_set', 'exit', 'wait', 'time', 'now', 'today', 'clear', 'uuid', 'random_string', 'sha256', 'md5', 'base64_encode', 'base64_decode'],
    ui: ['element', 'html', 'render', 'html_escape', 'css', 'signal', 'effect', 'serve', 'run', 'watch', 'config'],
    context: ['context_set', 'context_get', 'context_save', 'context_intents', 'context_add_convention', 'context_add_decision'],
    advanced: ['retry', 'retry_async', 'timeout', 'debounce', 'throttle', 'memoize', 'lazy', 'once'],
  },
  types: ['int', 'float', 'str', 'bool', 'none', 'list', 'dict', 'set', 'tuple', 'range', 'any', 'never', 'optional', 'result', 'promise', 'stream'],
  keywords: ['fn', 'class', 'trait', 'interface', 'impl', 'if', 'el:', 'for', 'in', 'while', 'ret', 'break', 'continue', 'let', 'mut', 'const', 'and', 'or', 'not', 'true', 'false', 'none', 'import', 'from', 'as', 'expose', 'module', 'match', 'test', 'doc', 'check', 'expect', 'type', 'enum', 'version', 'channel', 'schema', 'api', 'service', 'database', 'concurrent', 'permission', 'intent', 'async', 'await', 'spawn', 'yield', 'try', 'catch', 'throw', 'finally', 'raise', 'is', 'isnt', 'is not', 'in', 'not in', 'pass', 'self', 'super'],
  decorators: ['@retry', '@fallback', '@distributed', '@requires', '@ensures', '@invariant', '@expose', '@property', '@staticmethod', '@classmethod', '@cached', '@lazy', '@once'],
};

const SNIPPETS = {
  'fn': { label: 'fn', detail: 'Function', body: 'fn ${1:name}(${2:params}):\n  ${3:body}' },
  'fn->': { label: 'fn->', detail: 'Function with return type', body: 'fn ${1:name}(${2:params}) -> ${3:ReturnType}:\n  ${4:body}' },
  'class': { label: 'class', detail: 'Class', body: 'class ${1:Name}:\n  fn init(self${2:, params}):\n    ${3:body}' },
  'if': { label: 'if', detail: 'If', body: 'if ${1:condition}:\n  ${2:body}' },
  'el': { label: 'el:', detail: 'Else', body: 'el:\n  ${1:body}' },
  'elif': { label: 'el: if', detail: 'Else If', body: 'el: if ${1:condition}:\n  ${2:body}' },
  'for': { label: 'for', detail: 'For Loop', body: 'for ${1:item} in ${2:iterable}:\n  ${3:body}' },
  'while': { label: 'while', detail: 'While', body: 'while ${1:condition}:\n  ${2:body}' },
  'match': { label: 'match', detail: 'Match', body: 'match ${1:value}:\n  ${2:pattern}: ${3:result}\nel:\n  ${4:default}' },
  'test': { label: 'test', detail: 'Test', body: 'test ${1:name}():\n  ${2:body}' },
  'doc': { label: 'doc', detail: 'Documentation', body: 'doc "${1:description}"' },
  'check': { label: 'check', detail: 'Check Block', body: 'check ${1:name}:\n  ${2:body}' },
  'expect': { label: 'expect', detail: 'Expect', body: 'expect ${1:condition}, "${2:message}"' },
  'type': { label: 'type', detail: 'Type Alias', body: 'type ${1:Name} = ${2:Type}' },
  'enum': { label: 'enum', detail: 'Enum', body: 'enum ${1:Name}:\n  ${2:VARIANT}' },
  'schema': { label: 'schema', detail: 'Schema', body: 'schema ${1:Name}:\n  ${2:field}: ${3:type}' },
  'api': { label: 'api', detail: 'API', body: 'api ${1:METHOD} "${2:path}":\n  ${3:body}' },
  'service': { label: 'service', detail: 'Service', body: 'service ${1:Name}:\n  ${2:body}' },
  'database': { label: 'database', detail: 'Database', body: 'database ${1:Name}:\n  ${2:body}' },
  'concurrent': { label: 'concurrent', detail: 'Concurrent', body: 'concurrent ${1:name}:\n  ${2:body}' },
  'permission': { label: 'permission', detail: 'Permission', body: 'permission ${1:name} ${2:action} on ${3:resource}' },
  'intent': { label: 'intent', detail: 'Intent', body: '@intent_performance("${1:name}", budget_ms=${2:100})\nfn ${3:name}(${4:params}):\n  ${5:body}' },
  'try': { label: 'try', detail: 'Try-Catch', body: 'try:\n  ${1:body}\ncatch ${2:error}:\n  ${3:handler}' },
  'lambda': { label: '=>', detail: 'Lambda', body: '${1:x} => ${2:expr}' },
  'list': { label: '[]', detail: 'List', body: '[${1:items}]' },
  'dict': { label: '{}', detail: 'Dict', body: '{"${1:key}": ${2:value}}' },
};

function activate(context) {
  const diagnosticCollection = vscode.languages.createDiagnosticCollection('zpx');
  let zpxServer = null;

  context.subscriptions.push(
    // Commands
    vscode.commands.registerCommand('zpx.runFile', runFile),
    vscode.commands.registerCommand('zpx.runProject', runProject),
    vscode.commands.registerCommand('zpx.check', checkFile),
    vscode.commands.registerCommand('zpx.format', formatDocument),
    vscode.commands.registerCommand('zpx.restartServer', () => restartServer(context)),

    // Providers
    vscode.languages.registerCompletionItemProvider('zpx', new ZpxCompletionProvider(), '.', '(', '[', ',', '"', '\'', '@', ':', '<'),
    vscode.languages.registerHoverProvider('zpx', new ZpxHoverProvider()),
    vscode.languages.registerDefinitionProvider('zpx', new ZpxDefinitionProvider()),
    vscode.languages.registerDocumentFormattingEditProvider('zpx', new ZpxFormatter()),
    vscode.languages.registerCodeLensProvider('zpx', new ZpxCodeLensProvider()),
    vscode.languages.registerDocumentSymbolProvider('zpx', new ZpxDocumentSymbolProvider()),
    vscode.languages.registerWorkspaceSymbolProvider(new ZpxWorkspaceSymbolProvider()),

    diagnosticCollection
  );

  // Diagnostics on change
  const updateOnChange = vscode.workspace.onDidChangeTextDocument(e => {
    if (e.document.languageId === 'zpx') {
      updateDiagnostics(e.document, diagnosticCollection);
    }
  });
  context.subscriptions.push(updateOnChange);

  // Initial diagnostics
  if (vscode.window.activeTextEditor) {
    updateDiagnostics(vscode.window.activeTextEditor.document, diagnosticCollection);
  }

  // Start language server
  startLanguageServer(context);

  // Status bar
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.text = '$(zpx) Zpx';
  statusBar.tooltip = 'Zpx Language Support';
  statusBar.command = 'zpx.check';
  statusBar.show();
  context.subscriptions.push(statusBar);
}

async function startLanguageServer(context) {
  const config = vscode.workspace.getConfiguration('zpx');
  const serverPath = config.get('languageServerPath');
  
  if (serverPath && fs.existsSync(serverPath)) {
    try {
      const server = spawn(serverPath, ['--lsp'], { stdio: ['pipe', 'pipe', 'pipe'] });
      
      server.stdout.on('data', data => {
        // Handle LSP messages
      });
      
      server.stderr.on('data', data => {
        console.error('Zpx LSP:', data.toString());
      });
      
      zpxServer = server;
    } catch (e) {
      console.warn('Failed to start Zpx LSP:', e.message);
    }
  }
}

function restartServer(context) {
  if (zpxServer) {
    zpxServer.kill();
    zpxServer = null;
  }
  startLanguageServer(context);
  vscode.window.showInformationMessage('Zpx language server restarted');
}

async function runFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'zpx') {
    vscode.window.showErrorMessage('No Zpx file active');
    return;
  }
  await editor.document.save();
  const config = vscode.workspace.getConfiguration('zpx');
  const executablePath = config.get('executablePath', 'zpx');
  const terminal = vscode.window.createTerminal('Zpx Run');
  terminal.show();
  terminal.sendText(`${executablePath} run "${editor.document.fileName}"`);
}

async function runProject() {
  const workspace = vscode.workspace.workspaceFolders?.[0];
  if (!workspace) {
    vscode.window.showErrorMessage('No workspace open');
    return;
  }
  const config = vscode.workspace.getConfiguration('zpx');
  const executablePath = config.get('executablePath', 'zpx');
  const terminal = vscode.window.createTerminal('Zpx Project');
  terminal.show();
  terminal.sendText(`cd "${workspace.uri.fsPath}" && ${executablePath} run .`);
}

async function checkFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'zpx') {
    vscode.window.showErrorMessage('No Zpx file active');
    return;
  }
  await editor.document.save();
  const config = vscode.workspace.getConfiguration('zpx');
  const executablePath = config.get('executablePath', 'zpx');
  const terminal = vscode.window.createTerminal('Zpx Check');
  terminal.show();
  terminal.sendText(`${executablePath} check "${editor.document.fileName}"`);
}

async function formatDocument() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const doc = editor.document;
  const text = doc.getText();
  const formatted = formatZpxCode(text);
  if (text !== formatted) {
    const fullRange = new vscode.Range(doc.positionAt(0), doc.positionAt(text.length));
    await editor.edit(eb => eb.replace(fullRange, formatted));
  }
}

function formatZpxCode(code) {
  const lines = code.split('\n');
  const formatted = [];
  let indentLevel = 0;
  const indentSize = 2;
  const BLOCK_STARTS = /^(fn|class|trait|interface|if|el:|el:\s*if|for|while|match|test|doc|check|schema|api|service|database|concurrent|permission|concurrent)\b.*:\s*$/;
  const DECREASE = /^(el:|catch|finally)\b/;

  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed === '') { formatted.push(''); continue; }

    if (DECREASE.test(trimmed)) {
      indentLevel = Math.max(0, indentLevel - 1);
    }

    formatted.push(' '.repeat(indentLevel * indentSize) + trimmed);

    if (BLOCK_STARTS.test(trimmed)) {
      indentLevel++;
    }
  }
  return formatted.join('\n');
}

function updateDiagnostics(doc, collection) {
  if (doc.languageId !== 'zpx') return;
  const diagnostics = [];
  const text = doc.getText();
  const lines = text.split('\n');

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('#')) return;

    // return vs ret
    if (/\breturn\s+/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "ret" instead of "return"', vscode.DiagnosticSeverity.Warning));
    }

    // elif
    if (/\belif\b/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "el: if" instead of "elif"', vscode.DiagnosticSeverity.Warning));
    }

    // && ||
    if (/&&/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "and" instead of "&&"', vscode.DiagnosticSeverity.Warning));
    }
    if (/\|\|/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "or" instead of "||"', vscode.DiagnosticSeverity.Warning));
    }

    // function
    if (/\bfunction\b/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "fn" instead of "function"', vscode.DiagnosticSeverity.Warning));
    }

    // this
    if (/\bthis\b/.test(line)) {
      diagnostics.push(makeDiag(doc, i, 'Use "self" instead of "this"', vscode.DiagnosticSeverity.Warning));
    }

    // Missing colon
    if (/^\s*(fn|class|trait|interface|if|for|while|match|test|doc|check|schema|api|service|database|concurrent)\b.*[^:]\s*$/.test(line)) {
      if (!/['"#]/.test(line)) {
        diagnostics.push(makeDiag(doc, i, 'Missing colon at end of block statement', vscode.DiagnosticSeverity.Error));
      }
    }

    // Undefined variable (simple check)
    if (/\blet\s+(\w+)/.test(line)) {
      const varName = line.match(/\blet\s+(\w+)/)[1];
      // Check if used before definition in same scope - simplified
    }
  });

  collection.set(doc.uri, diagnostics);
}

function makeDiag(doc, line, msg, severity) {
  const range = new vscode.Range(line, 0, line, doc.lineAt(line).text.length);
  return new vscode.Diagnostic(range, msg, severity);
}

// ============ PROVIDERS ============

class ZpxCompletionProvider {
  provideCompletionItems(doc, pos, token, context) {
    const items = [];
    const lineText = doc.lineAt(pos).text.substring(0, pos.character);
    const triggerChar = context?.triggerCharacter;

    // Snippets
    if (triggerChar === ':') {
      const match = lineText.match(/^\s*(\w+)\s*$/);
      if (match && SNIPPETS[match[1]]) {
        return this.makeSnippet(SNIPPETS[match[1]]);
      }
    }

    // Keywords
    BUILTINS.keywords.forEach(kw => {
      items.push(this.makeItem(kw, vscode.CompletionItemKind.Keyword, 'Keyword'));
    });

    // Functions by category
    Object.entries(BUILTINS.functions).forEach(([cat, funcs]) => {
      funcs.forEach(fn => {
        const item = this.makeItem(fn, vscode.CompletionItemKind.Function, `Builtin (${cat})`);
        item.documentation = new vscode.MarkdownString(`**${fn}** - Zpx builtin function (${cat})`);
        items.push(item);
      });
    });

    // Types
    BUILTINS.types.forEach(t => {
      items.push(this.makeItem(t, vscode.CompletionItemKind.Class, 'Type'));
    });

    // Decorators
    BUILTINS.decorators.forEach(d => {
      items.push(this.makeItem(d, vscode.CompletionItemKind.Method, 'Decorator'));
    });

    // Snippets
    Object.values(SNIPPETS).forEach(s => {
      items.push(this.makeSnippet(s));
    });

    // Variable names from current document
    const varRegex = /\b(let|mut|const)\s+(\w+)/g;
    const text = doc.getText();
    let match;
    while ((match = varRegex.exec(text)) !== null) {
      items.push(this.makeItem(match[2], vscode.CompletionItemKind.Variable, 'Local variable'));
    }

    // Class names
    const classRegex = /^\s*class\s+(\w+)/gm;
    while ((match = classRegex.exec(text)) !== null) {
      items.push(this.makeItem(match[1], vscode.CompletionItemKind.Class, 'Class'));
    }

    // Function names
    const fnRegex = /^\s*fn\s+(\w+)/gm;
    while ((match = fnRegex.exec(text)) !== null) {
      items.push(this.makeItem(match[1], vscode.CompletionItemKind.Function, 'Function'));
    }

    return items;
  }

  makeItem(label, kind, detail) {
    const item = new vscode.CompletionItem(label, kind);
    item.detail = detail;
    return item;
  }

  makeSnippet(s) {
    const item = new vscode.CompletionItem(s.label, vscode.CompletionItemKind.Snippet);
    item.detail = s.detail;
    item.insertText = new vscode.SnippetString(s.body);
    return item;
  }
}

class ZpxHoverProvider {
  provideHover(doc, pos) {
    const word = doc.getWordRangeAtPosition(pos);
    if (!word) return null;
    const text = doc.getText(word);

    // Builtin docs
    const docs = {
      'print': 'Print to console\n\n```zpx\nprint("Hello")\nprint(1, 2, 3)  # multiple args\n```',
      'len': 'Length of string, list, or dict\n\n```zpx\nlen("hi")      # 2\nlen([1,2,3])   # 3\nlen({"a": 1})  # 1\n```',
      'str': 'Convert to string\n\n```zpx\nstr(42)       # "42"\nstr([1,2])    # "[1, 2]"\n```',
      'int': 'Convert to integer\n\n```zpx\nint("42")     # 42\nint(3.14)     # 3\n```',
      'float': 'Convert to float\n\n```zpx\nfloat("3.14") # 3.14\nfloat(42)     # 42.0\n```',
      'range': 'Generate range\n\n```zpx\nrange(5)      # [0,1,2,3,4]\nrange(2, 5)   # [2,3,4]\nrange(0, 10, 2) # [0,2,4,6,8]\n```',
      'abs': 'Absolute value\n\n```zpx\nabs(-5)  # 5\n```',
      'sqrt': 'Square root\n\n```zpx\nsqrt(16)  # 4.0\n```',
      'map': 'Map function over iterable\n\n```zpx\nmap([1,2,3], double)  # [2,4,6]\n```',
      'filter': 'Filter elements\n\n```zpx\nfilter([1,2,3], even)  # [2]\n```',
      'fn': 'Define function\n\n```zpx\nfn add(a, b):\n  ret a + b\n```',
      'class': 'Define class\n\n```zpx\nclass Dog:\n  fn init(self, name):\n    self.name = name\n```',
      'if': 'Conditional\n\n```zpx\nif x > 0:\n  print("pos")\nel:\n  print("neg")\n```',
      'for': 'For loop\n\n```zpx\nfor i in range(5):\n  print(i)\n```',
      'while': 'While loop\n\n```zpx\nwhile x < 10:\n  x = x + 1\n```',
      'ret': 'Return value\n\n```zpx\nfn add(a, b):\n  ret a + b\n```',
      'let': 'Variable declaration\n\n```zpx\nlet x = 42\n```',
      'self': 'Current instance\n\n```zpx\nclass Dog:\n  fn init(self, name):\n    self.name = name\n```',
      'and': 'Logical AND\n\n```zpx\nif x > 0 and x < 10:\n  print("in range")\n```',
      'or': 'Logical OR\n\n```zpx\nif x < 0 or x > 100:\n  print("out of range")\n```',
      'not': 'Logical NOT\n\n```zpx\nif not empty(list):\n  print("has items")\n```',
    };

    if (docs[text]) {
      return new vscode.Hover(new vscode.MarkdownString(docs[text]));
    }

    // Try to get signature from function definition
    const fnDoc = this.getFunctionDoc(doc, text);
    if (fnDoc) {
      return new vscode.Hover(new vscode.MarkdownString(fnDoc));
    }

    return null;
  }

  getFunctionDoc(doc, name) {
    const lines = doc.getText().split('\n');
    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(new RegExp(`^\\s*fn\\s+${name}\\s*\\(([^)]*)\\)`));
      if (match) {
        const params = match[1].trim();
        return `**fn ${name}(${params})**\n\nDefined at line ${i + 1}`;
      }
    }
    return null;
  }
}

class ZpxDefinitionProvider {
  provideDefinition(doc, pos) {
    const word = doc.getWordRangeAtPosition(pos);
    if (!word) return null;
    const text = doc.getText(word);
    const lines = doc.getText().split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.match(new RegExp(`^\\s*fn\\s+${text}\\s*\\(`))) {
        return new vscode.Location(doc.uri, new vscode.Position(i, 0));
      }
      if (line.match(new RegExp(`^\\s*class\\s+${text}\\b`))) {
        return new vscode.Location(doc.uri, new vscode.Position(i, 0));
      }
      if (line.match(new RegExp(`^\\s*let\\s+${text}\\s*=`))) {
        return new vscode.Location(doc.uri, new vscode.Position(i, 0));
      }
      if (line.match(new RegExp(`^\\s*class\\s+${text}\\b`))) {
        return new vscode.Location(doc.uri, new vscode.Position(i, 0));
      }
    }
    return null;
  }
}

class ZpxDocumentSymbolProvider {
  provideDocumentSymbols(doc) {
    const symbols = [];
    const lines = doc.getText().split('\n');

    lines.forEach((line, i) => {
      let match;
      if ((match = line.match(/^\s*fn\s+(\w+)/))) {
        symbols.push(new vscode.DocumentSymbol(
          match[1], 'Function', vscode.SymbolKind.Function,
          new vscode.Range(i, 0, i, line.length),
          new vscode.Range(i, 0, i, line.length)
        ));
      }
      if ((match = line.match(/^\s*class\s+(\w+)/))) {
        symbols.push(new vscode.DocumentSymbol(
          match[1], 'Class', vscode.SymbolKind.Class,
          new vscode.Range(i, 0, i, line.length),
          new vscode.Range(i, 0, i, line.length)
        ));
      }
      if ((match = line.match(/^\s*let\s+(\w+)/))) {
        symbols.push(new vscode.DocumentSymbol(
          match[1], 'Variable', vscode.SymbolKind.Variable,
          new vscode.Range(i, 0, i, line.length),
          new vscode.Range(i, 0, i, line.length)
        ));
      }
      if ((match = line.match(/^\s*(test|doc|check)\s+(\w+)/))) {
        symbols.push(new vscode.DocumentSymbol(
          match[2], match[1], vscode.SymbolKind.Method,
          new vscode.Range(i, 0, i, line.length),
          new vscode.Range(i, 0, i, line.length)
        ));
      }
    });

    return symbols;
  }
}

class ZpxWorkspaceSymbolProvider {
  provideWorkspaceSymbols(query) {
    // Would need file index - placeholder
    return [];
  }
}

class ZpxCodeLensProvider {
  provideCodeLenses(doc) {
    const lenses = [];
    const lines = doc.getText().split('\n');

    lines.forEach((line, i) => {
      const fnMatch = line.match(/^\s*fn\s+(\w+)\s*\(/);
      if (fnMatch) {
        const range = new vscode.Range(i, 0, i, line.length);
        lenses.push(new vscode.CodeLens(range, {
          title: '$(play) Run',
          command: 'zpx.runFile',
          tooltip: 'Run this file'
        }, {
          title: '$(beaker) Test',
          command: 'zpx.check',
          tooltip: 'Type-check this file'
        }));
      }
      if (line.match(/^\s*test\s+\w+/)) {
        const range = new vscode.Range(i, 0, i, line.length);
        lenses.push(new vscode.CodeLens(range, {
          title: '$(beaker) Run Test',
          command: 'zpx.runFile'
        }));
      }
    });

    return lenses;
  }
}

class ZpxFormatter {
  provideDocumentFormattingEdits(doc) {
    const edits = [];
    const text = doc.getText();
    const formatted = formatZpxCode(text);

    if (text !== formatted) {
      const range = new vscode.Range(doc.positionAt(0), doc.positionAt(text.length));
      edits.push(vscode.TextEdit.replace(range, formatted));
    }
    return edits;
  }
}

function deactivate() {
  if (zpxServer) {
    zpxServer.kill();
  }
}

module.exports = { activate, deactivate };