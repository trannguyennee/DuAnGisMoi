# Security Policy

If you find a security issue in this project, please **do not open a public issue**.
Report it privately via GitHub → **Security → Report a vulnerability** on this repository.

## What is checked automatically

Every push and pull request runs the [DevSecOps pipeline](.github/workflows/devsecops.yml):

| Gate | Tool | Fails the build when |
|---|---|---|
| Secrets | gitleaks | a key, token or password is committed |
| SAST | bandit | risky Python patterns are found |
| SCA | pip-audit | a dependency has a known CVE |
| Tests | Django test suite on PostGIS | a security regression test fails |
| Config | `manage.py check --deploy` | production settings are unsafe |

Dependabot opens weekly PRs for outdated pip packages and GitHub Actions.
