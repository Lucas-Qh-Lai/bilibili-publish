# Security Policy

## Credentials

This skill handles a Bilibili session cookie in order to publish on your behalf.

- `cookies.json` is a **temporary credential**. Delete it after verification.
- Never commit `cookies.json`, `publish_result.json`, `.env`, or any exported
  account data. They are listed in `.gitignore`.
- Never paste cookie values into issues, pull requests, screenshots, or reports.
- `extract_bili_cookies.py` writes the cookie file with mode `0600`.

If you believe a credential has been exposed, revoke the session (log out of the
Bilibili client) and re-extract.

## Scope

This project only publishes a video that you already own and control. It does
not bypass platform authentication, does not decrypt the client database, and
does not implement the replace-source endpoint.

## Reporting

Open an issue for non-sensitive problems. For anything involving credentials or
account security, do not open a public issue.
