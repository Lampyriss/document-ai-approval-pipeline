# Security And Sanitization

This repository is prepared for public portfolio use.

## Removed Or Replaced

- API keys and access tokens
- signed Power Automate trigger URLs
- tenant IDs, environment IDs, and connector reference names
- direct links to the live academic SharePoint site
- personal email addresses and contact names
- temp exports, local backups, caches, and editor state

## Converted To Examples

- dashboard links now read from environment variables
- public URLs use `example.com`, `example.edu`, or `contoso.sharepoint.com`
- Power Automate exports are replaced with sanitized reference documents

## Before Publishing Your Own Version

1. Rotate any secret that ever existed in a tracked workspace or commit history.
2. Use a fresh GitHub repository instead of publishing the original history.
3. Re-scan docs, JSON exports, CSV files, and screenshots for personal data.
4. Keep `.env` files, `*.secrets.json`, and generated databases out of version control.

## Why This Matters

Portfolio repositories should show system design and implementation quality without exposing operational details from a real tenant. This copy is set up to preserve the architecture story while reducing avoidable risk.
