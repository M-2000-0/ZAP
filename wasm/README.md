# Zpx WebAssembly Target

Compile Zpx code to WebAssembly for browser execution.

## Status

**Experimental** - This is a proof-of-concept implementation.

## How It Works

1. Zpx code is transpiled to JavaScript
2. JavaScript is compiled to WebAssembly using existing tools
3. WebAssembly runs in the browser

## Usage

### From CLI

```bash
# Compile Zpx to WebAssembly
zpx compile main.zpx --target wasm

# This generates:
# - main.wasm (WebAssembly binary)
# - main.js (JavaScript glue code)
```

### In HTML

```html
<!DOCTYPE html>
<html>
<head>
    <title>Zpx WebAssembly</title>
</head>
<body>
    <script src="main.js"></script>
    <script>
        // Call Zpx functions from JavaScript
        const result = zpx.add(2, 3);
        console.log(result);  // 5
    </script>
</body>
</html>
```

### From JavaScript

```javascript
// Load the WebAssembly module
const zpx = await ZpxModule.init();

// Call Zpx functions
const result = zpx.fibonacci(10);
console.log(result);  // 55
```

## Supported Features

- [x] Basic arithmetic
- [x] Variables
- [x] Functions
- [x] If/else statements
- [x] While loops
- [x] For loops
- [x] Lists
- [x] Strings
- [x] Print function
- [ ] Classes (coming soon)
- [ ] Import system (coming soon)
- [ ] Standard library (coming soon)

## Example

### Zpx Code

```zpx
fn fibonacci(n):
  if n <= 1:
    ret n
  let a = 0
  let b = 1
  let i = 2
  while i <= n:
    let temp = a + b
    a = b
    b = temp
    i = i + 1
  ret b

print(fibonacci(10))
```

### Compiled JavaScript

```javascript
function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    let a = 0;
    let b = 1;
    let i = 2;
    while (i <= n) {
        let temp = a + b;
        a = b;
        b = temp;
        i = i + 1;
    }
    return b;
}

console.log(fibonacci(10));
```

## Building

```bash
# Install dependencies
cd wasm
npm install

# Build the compiler
npm run build

# Test with example
npm test
```

## Limitations

- No direct WebAssembly compilation yet (uses JS transpilation)
- Limited standard library support
- No class support in WASM target
- No module system support

## Future Plans

- Direct WebAssembly compilation using Binaryen
- Full standard library support
- Class and object support
- Module system
- Optimizations for size and speed
