# Contributing — Team ARAJ

## Branch Strategy
```
main          ← protected. Ashfaaq merges only.
dev           ← all PRs target this branch first
arpan/classifier       ← Arpan's ML work
jyoti/data-docs        ← Jyoti's dataset + docs
ranjeet/fraud-testing  ← Ranjeet's fraud + QA
```

## Daily Workflow

```bash
# Always start from dev
git checkout dev
git pull origin dev

# Create your branch
git checkout -b yourname/what-you-are-doing

# Work, then commit
git add .
git commit -m "feat: short description of what you did"

# Push
git push origin yourname/what-you-are-doing

# Then open a Pull Request to dev on GitHub
```

## Commit Message Format

```
feat:     new feature or module
fix:      bug fix
data:     dataset changes or additions
docs:     documentation only
test:     test scripts or results
chore:    cleanup, config changes
```

Examples:
```
feat: add blur detection to OCR pipeline
data: add 50 Indian receipt images to labels.csv
fix: handle Gemini 429 rate limit in upload route
```

## Pull Request Rules

- Title must describe what changed
- Add a short description of what you did and why
- Tag Ashfaaq as reviewer on every PR
- Do not merge your own PR
- PRs to main require Ashfaaq approval only

## Never Do This

- Never push directly to main
- Never commit .env or serviceAccountKey.json
- Never commit large model files without Git LFS
- Never commit dataset images (use external storage)
