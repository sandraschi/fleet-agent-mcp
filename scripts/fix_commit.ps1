# Script to remove node_modules from git tracking
git rm -r --cached webapp/node_modules
git add -A src/ workflows/ README.md .gitignore pyproject.toml
git commit -m "PR pipeline: codegen + github tools (31 tools)"
