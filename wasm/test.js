#!/usr/bin/env node

/**
 * Test the Zap to JavaScript transpiler
 */

const ZapToJS = require('./zap-to-js');

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
        name: 'String operations',
        zap: 'let len = len("hello")',
        expected: 'let len = Array.isArray("hello") ? "hello".length : "hello".length;'
    }
];

const transpiler = new ZapToJS();
let passed = 0;
let failed = 0;

for (const test of testCases) {
    try {
        const result = transpiler.transpile(test.zap);
        if (result.trim() === test.expected.trim()) {
            console.log(`✓ ${test.name}`);
            passed++;
        } else {
            console.log(`✗ ${test.name}`);
            console.log(`  Expected: ${test.expected}`);
            console.log(`  Got:      ${result.trim()}`);
            failed++;
        }
    } catch (e) {
        console.log(`✗ ${test.name} - Error: ${e.message}`);
        failed++;
    }
}

console.log(`\n${passed} passed, ${failed} failed`);

if (failed > 0) {
    process.exit(1);
}
