from django_typer.management import Typer
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
    Case,
    IndividualOpinion,
    Person,
    Tenure,
    Alias,
    SelectionType,
    PersonGender,
    PersonRace,
    PartyAffiliation,
)

app = Typer()


@app.command()
def command(self, arg):
    add = "add" in arg
    update = "update" in arg

    all_aliases = Alias.objects.all()
    for alias in all_aliases:
        if add:
            alias.match_tenure(update)
        else:
            matches = alias.find_matches()
            print(matches)
