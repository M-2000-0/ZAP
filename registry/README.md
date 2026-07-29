# Zpx Package Registry

A simple, Git-based package registry for Zpx packages.

## How It Works

The Zpx registry uses Git repositories as package sources. Each package is a Git repository with a `zpx-package.json` file.

### Package Structure

```
my-package/
├── zpx-package.json    # Package metadata
├── src/
│   └── main.zpx        # Package code
└── README.md
```

### zpx-package.json

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "My awesome Zpx package",
  "author": "Your Name",
  "repository": "https://github.com/username/my-package",
  "main": "src/main.zpx",
  "dependencies": {},
  "keywords": ["zpx", "package"]
}
```

## Usage

### Installing Packages

```bash
# Install from GitHub
zpx add github:username/package-name

# Install from URL
zpx add https://github.com/username/package-name

# Install specific version
zpx add github:username/package-name@v1.0.0
```

### Publishing Packages

1. Create a Git repository with your package
2. Add a `zpx-package.json` file
3. Push to GitHub
4. Users can now install with `zpx add github:username/package-name`

### Listing Packages

```bash
# List installed packages
zpx list

# Search packages (future)
zpx search "http"
```

## Official Packages

| Package | Description |
|---------|-------------|
| `zpx-db` | Database operations |
| `zpx-http` | HTTP client |
| `zpx-ai` | AI/ML primitives |
| `zpx-deploy` | Deployment helpers |

## Creating a Package

1. Create a new directory
2. Initialize with `zpx-package.json`
3. Write your code in `src/main.zpx`
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
