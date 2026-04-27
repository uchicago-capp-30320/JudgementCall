<<<<<<< HEAD
from django.shortcuts import render
from django.http import HttpResponse
from .models import (
    Court,
    Person,
    Election,
    Candidacy,
    Tenure,
    Case,
    IndividualOpinion,
    CourtType,
    SelectionType,
    CaseType,
    PartyAffiliation,
)
from datetime import date
import random
from faker import Faker


def add_fake_data(request):
    fake = Faker("en_US")

    # create Persons
    for _ in range(10):
        Person.objects.create(
            name=fake.name(),
            birth_date=fake.date_between(start_date="-150y", end_date="-22y"),
            gender=fake.passport_gender(),
            race=random.choice(["White", "Black", "Asian"]),
            party_registration=random.choice(["Republican", "Democrat", "Independent", "Other"]),
            professional_experience=fake.text(),
        )

    # create courts
    courts = [
        {
            "org_id": "ILSUP",
            "name": "Illinois Supreme Court",
            "court_type": CourtType.SUPREME,
            "bench_size": 7,
            "selection_type": SelectionType.PARTISAN,
            "selection_method": "Partisan election with retention votes",
            "term_length": 10,
            "url": "https://www.illinoiscourts.gov",
        },
        {
            "org_id": "AZSUP",
            "name": "Arizona Supreme Court",
            "court_type": CourtType.SUPREME,
            "bench_size": 5,
            "selection_type": SelectionType.APPOINTMENT,
            "selection_method": "Merit selection with retention election",
            "term_length": 6,
            "url": "https://www.azcourts.gov",
        },
        {
            "org_id": "ILAPP1",
            "name": "Illinois Appellate Court First District",
            "court_type": CourtType.APPELLATE,
            "bench_size": 24,
            "selection_type": SelectionType.PARTISAN,
            "selection_method": "Partisan election with retention votes",
            "term_length": 10,
            "url": "https://www.illinoiscourts.gov",
        },
    ]

    for court_data in courts:
        Court.objects.get_or_create(org_id=court_data["org_id"], defaults=court_data)

    # create elections

    # make a dictionary of the courts
    court_objects = {}
    for court in Court.objects.all():
        court_objects[court.org_id] = court

    elections = [
        {
            "court": court_objects["ILSUP"],
            "date": date(2028, 11, 7),
        },
        {
            "court": court_objects["AZSUP"],
            "date": date(2028, 11, 7),
        },
        {
            "court": court_objects["ILAPP1"],
            "date": date(2028, 11, 7),
        },
        {
            "court": court_objects["ILSUP"],
            "date": date(2024, 11, 7),
        },
        {
            "court": court_objects["AZSUP"],
            "date": date(2024, 11, 7),
        },
        {
            "court": court_objects["ILAPP1"],
            "date": date(2024, 11, 7),
        },
    ]

    for election_data in elections:
        Election.objects.get_or_create(court=election_data["court"], date=election_data["date"])

    # create candidacies
    persons = list(Person.objects.all())
    election_objects = list(Election.objects.all())

    for election in election_objects:
        candidates = random.sample(persons, k=random.randint(2, 5))
        for person in candidates:
            Candidacy.objects.get_or_create(person=person, election=election)

    # create tenures
    for _ in range(3):
        for person in persons:
            court = random.choice(list(court_objects.values()))
            selection = random.choice(SelectionType.values)
            start = fake.date_between(start_date=date(1950, 1, 1), end_date=date(2020, 1, 1))
            end = fake.date_between(start_date=start, end_date=date(2024, 1, 1))
            appointer_party = (
                random.choice(PartyAffiliation.values)
                if selection == SelectionType.APPOINTMENT
                else ""
            )

            Tenure.objects.get_or_create(
                court=court,
                person=person,
                defaults={
                    "start_date": start,
                    "end_date": end,
                    "selection_type": selection,
                    "ticket_party": (
                        random.choice(PartyAffiliation.values)
                        if selection == SelectionType.PARTISAN
                        else ""
                    ),
                    "appointer_name": (
                        fake.name() if selection == SelectionType.APPOINTMENT else ""
                    ),
                    "appointer_party": appointer_party,
                    "chief_justice": random.choice([True, False]),
                },
            )

    # create cases
    for _ in range(10):
        Case.objects.create(
            docket_no=fake.bothify(text="??-####"),
            case_type=random.choice(CaseType.values),
            case_title=fake.sentence(nb_words=5),
            description=fake.text(),
            pro_con=random.choice(["pro", "con"]),
            decision_status=random.choice([True, False]),
            decision_outcome=random.choice(
                [
                    "Def good for justice",
                    "This one owned the libs",
                    "This one killed all the penguins",
                    "This one was about motorcycles",
                ]
            ),
        )

    # create individual opinions
    cases = list(Case.objects.all())
    tenures = list(Tenure.objects.all())

    for case in cases:
        opinion_writers = random.sample(tenures, k=random.randint(2, 3))
        for tenure in opinion_writers:
            IndividualOpinion.objects.get_or_create(
                case=case, tenure=tenure, defaults={"description": fake.text()}
            )

    return HttpResponse("Done!")
=======
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from .models import DataSet, Publisher, Region, DataSetFile
from urllib.parse import urlparse


def landing(request):
    """Landing page for Judgement Call users."""
    context = {
        "msg": "Welcome to Judgement Call!",
    }

    return render(request, "home.html", context)
>>>>>>> 37e0d64 (commit needed to pull?)
