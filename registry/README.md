# Zap Package Registry

A simple, Git-based package registry for Zap packages.

## How It Works

The Zap registry uses Git repositories as package sources. Each package is a Git repository with a `zap-package.json` file.

### Package Structure

```
my-package/
├── zap-package.json    # Package metadata
├── src/
│   └── main.zap        # Package code
└── README.md
```

### zap-package.json

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "My awesome Zap package",
  "author": "Your Name",
  "repository": "https://github.com/username/my-package",
  "main": "src/main.zap",
  "dependencies": {},
  "keywords": ["zap", "package"]
}
```

## Usage

### Installing Packages

```bash
# Install from GitHub
zap add github:username/package-name

# Install from URL
zap add https://github.com/username/package-name

# Install specific version
zap add github:username/package-name@v1.0.0
```

### Publishing Packages

1. Create a Git repository with your package
2. Add a `zap-package.json` file
3. Push to GitHub
4. Users can now install with `zap add github:username/package-name`

### Listing Packages

```bash
# List installed packages
zap list

# Search packages (future)
zap search "http"
```

## Official Packages

| Package | Description |
|---------|-------------|
| `zap-db` | Database operations |
| `zap-http` | HTTP client |
| `zap-ai` | AI/ML primitives |
| `zap-deploy` | Deployment helpers |

## Creating a Package

1. Create a new directory
2. Initialize with `zap-package.json`
3. Write your code in `src/main.zap`
4. Push to GitHub
5. Share the URL with users

## Package Guidelines

- Use descriptive names
- Include a README.md
- Add version numbers (semver)
- Keep packages focused (do one thing well)
- Add tests if possible

## Future

- Package registry website
- Search functionality
- Version management
- Dependency resolution
- Auto-publishing from CLI
