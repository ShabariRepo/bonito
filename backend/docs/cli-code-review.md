# Bonito CLI: `init-review` Command Spec

## Overview

`bonito-cli init-review` is a one-liner setup command that configures automated AI code reviews for any GitHub repository using GitHub Actions. This is the **alternative path** for users who prefer not to install the Bonito GitHub App.

## Usage

```bash
npx bonito-cli init-review
```

Or if installed globally:

```bash
bonito-cli init-review
```

## What It Does

1. **Auto-detects the GitHub repo** — reads `.git/config` to find the remote origin
2. **Prompts for API key** — or reads from `BONITO_API_KEY` environment variable
3. **Creates `.github/workflows/bonito-review.yml`** — a minimal GitHub Actions workflow
4. **Adds `BONITO_API_KEY` instructions** — tells the user to add it as a GitHub secret

## Interactive Flow

```
$ npx bonito-cli init-review

🐟 Bonito AI Code Review Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Detected repo: octocat/my-project
✓ Branch: main

? Enter your Bonito API key (or set BONITO_API_KEY env var):
  → bn-xxxxxxxxxxxxxxxxxxxx

Creating .github/workflows/bonito-review.yml...  ✓

Next steps:
  1. Add BONITO_API_KEY as a GitHub repository secret
     → Settings → Secrets → Actions → New repository secret
  2. Push this commit to trigger reviews on your next PR

Done! 🎉 Bonito will review every PR automatically.
```

## Generated Workflow File

`.github/workflows/bonito-review.yml`:

```yaml
name: Bonito AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Bonito Code Review
        uses: getbonito/bonito-review-action@v1
        with:
          bonito-api-key: ${{ secrets.BONITO_API_KEY }}
          # Optional configuration:
          # severity-threshold: warning  # Only post comments for warnings and above
          # max-files: 50               # Skip review if PR has too many files
          # skip-patterns: "*.lock,*.min.js,dist/**"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BONITO_API_KEY` | Yes | Your Bonito API key (starts with `bn-`) |
| `BONITO_SEVERITY_THRESHOLD` | No | Minimum severity to report: `critical`, `warning`, `suggestion` (default: `suggestion`) |
| `BONITO_MAX_FILES` | No | Maximum files to review per PR (default: 50) |
| `BONITO_SKIP_PATTERNS` | No | Comma-separated glob patterns to skip |

## CLI Flags

```
bonito-cli init-review [options]

Options:
  --api-key <key>     Bonito API key (default: reads BONITO_API_KEY)
  --workflow-only      Only generate the workflow file, skip prompts
  --severity <level>   Set default severity threshold
  --dry-run           Print the workflow file without writing it
  --help              Show help
```

## GitHub Actions vs GitHub App

| Feature | GitHub App | GitHub Actions (CLI) |
|---------|-----------|---------------------|
| Setup | One-click install | Run CLI + add secret |
| Config | Zero config | Workflow file in repo |
| Updates | Automatic | Update action version |
| Privacy | Diff sent to Bonito API | Diff sent to Bonito API |
| Free tier | 5 reviews/month | 5 reviews/month |
| Pro tier | Unlimited | Unlimited |
| Works with | GitHub.com | GitHub.com + GHES |

## Implementation Notes

### Package Structure

```
packages/bonito-cli/
├── package.json
├── bin/
│   └── bonito-cli.js          # CLI entry point
├── src/
│   ├── commands/
│   │   └── init-review.ts     # init-review command
│   ├── utils/
│   │   ├── git.ts             # Git repo detection
│   │   └── prompts.ts         # Interactive prompts
│   └── templates/
│       └── bonito-review.yml  # Workflow template
└── README.md
```

### Dependencies

- `commander` — CLI framework
- `inquirer` — Interactive prompts
- `chalk` — Terminal styling
- `yaml` — YAML generation
- `simple-git` — Git repo detection

### Future Enhancements

- `bonito-cli review <file>` — Review a single file or diff
- `bonito-cli review --pr <number>` — Review a specific PR
- `bonito-cli config` — Configure default settings
- `bonito-cli usage` — Check review usage for the month
- Support for GitLab CI and Bitbucket Pipelines
