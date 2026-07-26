# Zap Language for VS Code

AI-native full-stack language support for Visual Studio Code.

## Features

- **Syntax Highlighting** - Full syntax highlighting for Zap language
- **Autocomplete** - Smart code completion for keywords, built-in functions, and snippets
- **Error Checking** - Real-time diagnostics for common Zap mistakes
- **Code Formatting** - Automatic formatting on save
- **Code Lens** - Run buttons for functions
- **Hover Documentation** - Built-in function documentation on hover
- **Go to Definition** - Jump to function/class definitions
- **Snippets** - Common Zap patterns as snippets

## Installation

### From VSIX

1. Build the extension:
   ```bash
   cd vscode-extension
   npm run package
   ```

2. Install the extension:
   ```bash
   code --install-extension zap-language-0.1.0.vsix
   ```

### From Source

1. Clone the repository
2. Open the `vscode-extension` folder in VS Code
3. Press `F5` to launch the extension development host

## Usage

### Running Zap Files

1. Open a `.zap` file
2. Press `Ctrl+Shift+P` and select "Zap: Run Current File"
3. Or right-click in the editor and select "Run Zap File"

### Formatting

1. Open a `.zap` file
2. Press `Shift+Alt+F` to format the document
3. Or enable auto-format on save in settings

### Autocomplete

Type in a `.zap` file and suggestions will appear automatically. You can also press `Ctrl+Space` to trigger suggestions manually.

### Snippets

Type a snippet prefix and press `Tab` to expand. Available snippets:

- `fn` - Function definition
- `class` - Class definition
- `if` - If statement
- `el:` - Else statement
- `for` - For loop
- `while` - While loop
- `match` - Pattern matching
- `try` - Try-catch
- `schema` - Schema definition
- `api` - API endpoint
- `service` - Service definition

## Settings

- `zap.executablePath` - Path to the Zap executable (default: "zap")
- `zap.autoFormat` - Auto-format on save (default: true)
- `zap.lintEnabled` - Enable real-time linting (default: true)

## Known Issues

- Limited support for complex type annotations
- No debugger support yet
- No remote development support

## Contributing

Contributions are welcome! Please see the [main repository](https://github.com/M-2000-0/ZAP) for details.

## License

MIT
