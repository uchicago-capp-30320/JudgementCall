# Judgement Call

Judgement Call is a civic education project on state-level judiciaries and judicial elections. 

## Getting Started

This project uses uv for virtual environment and dependency management. See https://docs.astral.sh/uv/getting-started/installation/ for setup instructions.

#### Ingestion
TO DO:
- run a command from the command line to ingest datasets (courts, judges, cases, etc) and update table

#### Django Instructions
TODO

## File System Layout
- `apps/` - Parent directory for project apps.
- `apps/judgementcall/` - The main Judgement Call app directory. Contains the data models, views and tests for the web app. 
- `apps/accounts/` - An app that defines the DJOK custom user model, compatible with `allauth` and `django.contrib.admin`.
- `config/` - Config directory for the Django project.
- `data/` - Data directory.
- `ingestion/` - Backend data ingestion functions to populate the project database.
- `static/` - Static CSS, images and JS files.
- `templates/` - Django frontend templates.


## Attribution

Django project template: https://codeberg.org/jpt/djok

## Contributors
- Alexandrea Harriott
- Callie Leone
- Liberto de Pablo
- Maggie Larson
- Riley Kouns
- Riley Morrison
