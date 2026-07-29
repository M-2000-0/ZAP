#!/usr/bin/env node

const ZapToJS = require('./zpx-to-js');

const testCases = [
    {
        name: 'Hello World',
        zap: 'print("Hello, World!")',
        expected: 'console.log("Hello, World!");'
    },
    {
        name: 'Variable',
        zap: 'let x = 42',
        expected: 'let x = 42;'
    },
    {
        name: 'Function',
        zap: 'fn add(a, b):\n  ret a + b',
        expected: 'function add(a, b) {\n  return a + b;\n}'
    },
    {
        name: 'If statement',
        zap: 'if x > 0:\n  print("positive")',
        expected: 'if (x > 0) {\n  console.log("positive");\n}'
    },
    {
        name: 'If/else',
        zap: 'if x > 0:\n  print("pos")\nel:\n  print("neg")',
        expected: 'if (x > 0) {\n  console.log("pos");\n} else {\n  console.log("neg");\n}'
    },
    {
        name: 'While loop',
        zap: 'while i < 10:\n  i = i + 1',
        expected: 'while (i < 10) {\n  i = i + 1;\n}'
    },
    {
        name: 'For loop',
        zap: 'for item in items:\n  print(item)',
        expected: 'for (const item of items) {\n  console.log(item);\n}'
    },
    {
        name: 'List',
        zap: 'let nums = [1, 2, 3]',
        expected: 'let nums = [1, 2, 3];'
    },
    {
        name: 'Len builtin',
        zap: 'let n = len(data)',
        expected: 'let n = (data).length;'
    },
    {
        name: 'Str builtin',
        zap: 'let s = str(42)',
        expected: 'let s = String(42);'
    },
    {
        name: 'Sqrt builtin',
        zap: 'let r = sqrt(9)',
        expected: 'let r = Math.sqrt(9);'
    },
    {
        name: 'Boolean operators',
        zap: 'let v = a and b or not c',
        expected: 'let v = a && b || ! c;'
    },
    {
        name: 'None literal',
        zap: 'let v = none',
        expected: 'let v = null;'
    },
    {
        name: 'True literal',
        zap: 'let v = true',
        expected: 'let v = true;'
    },
    {
        name: 'Self reference',
        zap: '  ret self',
        expected: '  return this;'
    },
    {
        name: 'Method with self',
        zap: '  fn get_value(self):\n    ret self.value',
        expected: '  get_value() {\n    return this.value;\n  }',
        inClass: true
    }
];

const transpiler = new ZapToJS();
let passed = 0;
let failed = 0;

for (const test of testCases) {
    try {
        let zapCode = test.zap;
        if (test.inClass) {
            zapCode = 'class Foo:\n' + test.zap;
        }

        const result = transpiler.transpile(zapCode).trim();
        const expected = test.expected.trim();

        if (result.includes(expected)) {
            console.log(`  ${test.name}`);
            passed++;
        } else {
            console.log(`  ${test.name}`);
            console.log(`    Expected: ${expected}`);
            console.log(`    Got:      ${result}`);
            failed++;
        }
    } catch (e) {
        console.log(`  ${test.name} - Error: ${e.message}`);
        failed++;
    }
}

console.log(`\n${passed} passed, ${failed} failed out of ${testCases.length} tests`);

if (failed > 0) {
    process.exit(1);
}
