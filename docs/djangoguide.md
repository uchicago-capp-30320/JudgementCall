## Django admin

Note: if running into a SECRET_KEY error in development, make sure to set the DEBUG environment variable to True.
- Windows/Powershell: `$env:DEBUG=$true`
- Mac:

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