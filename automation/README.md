# Automation References

This folder contains portfolio-safe reference files for the two main Power Automate flows used in the project.

- `flow1.sanitized.json`: intake, OCR, storage, and advisor approval kickoff
- `flow2.sanitized.json`: instructor approval, office approval, and final document generation

These files are not direct exports from a live tenant. They are curated summaries that preserve the architecture and action sequence while removing:

- connector reference IDs
- tenant IDs and environment IDs
- signed webhook URLs
- live SharePoint site links
- real email addresses and personal names

For actual deployment, recreate the connectors and expressions in your own Power Platform environment.
