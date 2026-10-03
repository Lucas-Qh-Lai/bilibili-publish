# Contributing

## Scope

This project is deliberately narrow: **publishing only**. Pull requests that add
video production, TTS, slide generation, or editing are out of scope.

Changes that are in scope:

- Bug fixes in the publish / verify / credential-extraction flow
- Better error messages and pre-flight checks
- Documentation corrections
- New Bilibili API fields that affect publishing

## Rules

1. **Never commit credentials, cookies, tokens, or `publish_result.json`.**
2. **Do not add the replace-source endpoint.** Replacing the video source of a
   published archive is explicitly out of scope.
3. Keep scripts dependency-light. `requests` is the only hard requirement.
4. Preserve the upstream attribution in `README.md`, `README.en.md`, and
   `THIRD_PARTY_NOTICES.md`. Do not remove or weaken it.
5. Run the checks before opening a PR:

```bash
python3 -m py_compile scripts/*.py
zsh -n scripts/extract_bili_login_macos.sh
python3 scripts/check_dependencies.py
```

## Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes:
`feat:`, `fix:`, `docs:`, `chore:`.
