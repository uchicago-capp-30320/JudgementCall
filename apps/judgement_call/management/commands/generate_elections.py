from django.core.management.base import BaseCommand
from django_typer.management import Typer
from apps.judgement_call.models import (
    Election,
)

app = Typer()


class Command(BaseCommand):
    help = "Matches aliases against names of judges in the tenure table"

    def handle(self, **options):
        Election.deduce_elections(self)
