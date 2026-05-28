## Django admin

Note: if running into a SECRET_KEY error in development, make sure to set the DEBUG environment variable to True.
- Windows/Powershell: `$env:DEBUG=$true`
- Mac: `export DEBUG="true"`

### Set up to use the Django admin view
#### First time

1. Run account migrations
- Run `uv run python manage.py migrate`
- This will create the user accounts tables in db.sqlite3 necessary to add superusers

2. Create superuser
- Run `uv run python manage.py createsuperuser`
- Enter your username, email and password
- For now, this is stored in db.sqlite3, so will be deleted if you delete your local version of the database

3. Try running server
- Run `uv run python manage.py runserver`
- Navigate to http://127.0.0.1:8000/djadmin
- Check that the page loads

#### To view judgement_call tables

4. Make sure migrations are up to date
- Pull any migrations and run `uv run python manage.py migrate`
- OR: run `uv run python manage.py makemigrations` followed by `uv run python manage.py migrate`, but make sure to delete new migration files from `apps/judgement_call/migrations` before committing any changes unless you're SURE you are supposed to be creating migration files

5. Navigate to admin
- Run `uv run python manage.py runserver`
- Navigate to http://127.0.0.1:8000/djadmin
- You should see all tables in the admin view
- You can add records manually here; these will be created in your local sqlite database

#### To reset changes

6. Delete database
- Run git status to check if anyone new files have been created, especially in `apps/judgement_call/migrations` - if you have accidentally created new migration files be careful not to commit them!
- To clear any records you've created, just delete your local db.sqlite3 database - this is your local database and shouldn't affect anyone else
- This will also delete your superuser record


### To populate database with data
0. Set your debug environment variable, make sure superuser is set up, make sure migrations are up to date, etc.
Run all commands from root directory.
1. Create courts CSVs: set CL_API_KEY environment variable to CourtListener API key, then run `uv run python -m ingestion.ingest_courts`. This will take a couple minutes to create the csv files the first time; if the files already exist, ingest_courts will read from the csv files.
2. Run ingestion commands in this order:
- `uv run manage.py ingest courts` - will create court records
- `uv run manage.py ingest cases` - will create case records & link to court records
- `uv run manage.py ingest individual-opinions` - will create individual opinion records & link to case records, and will also create alias records for each individual opinion
- `uv run manage.py ingest county-to-court` - will create geographic crosswalks to courts
- `uv run manage.py ingest tenures` - will create judge tenure and associated person records (NB: This does not link canonical person name records to aliases)
- `uv run manage.py ingest elections` - will create election records, each record being a single upcoming seat
- `uv run manage.py ingest candidacies` - will create candidacy records & link to election records
3. Run manage commands in this order:
- `uv run manage.py match_aliases add=false update=false` - will link canonical person name records to the alias records ingested from cases