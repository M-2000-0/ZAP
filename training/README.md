# Zap Training Dataset for LLMs

This directory contains training data for fine-tuning language models to generate Zap code.

## Files

- `zap-training-data.jsonl` - 40 prompt-completion pairs for fine-tuning

## Format

Each line is a JSON object with:
- `prompt` - Natural language description of what to code
- `completion` - Zap code that implements the feature

Example:
```json
{"prompt": "Write a function that calculates the factorial of a number", "completion": "fn factorial(n):\n  if n <= 1:\n    ret 1\n  ret n * factorial(n - 1)"}
```

## Usage

### Fine-tuning with OpenAI

```bash
# Upload the training file
openai api files.upload -f training/zap-training-data.jsonl -p purpose fine-tune

# Create a fine-tuning job
openai api fine_tuning.jobs.create -t <file-id> -m gpt-4o-mini
```

### Fine-tuning with Hugging Face

```python
from datasets import load_dataset

dataset = load_dataset("json", data_files="zap-training-data.jsonl")
# ... training code
```

## Contributing

To add more training examples:

1. Add a new line to `zap-training-data.jsonl`
2. Follow the format: `{"prompt": "...", "completion": "..."}`
3. Ensure the Zap code is correct and follows the style guide

## Quality Guidelines

- Use clear, descriptive prompts
- Write idiomatic Zap code
- Include comments for complex logic
- Cover a variety of use cases
- Keep examples concise but complete
