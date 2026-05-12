from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Avg, Count, When, Value, Q
from django.db.models import Case as Case_
from .models import (
    Court,
    Person,
    Election,
    Candidacy,
    Tenure,
    Case,
    IndividualOpinion,
    CourtLevel,
    SelectionType,
    CaseType,
    SelectionJurisdictionType,
    Alias,
    CaseParticipant,
    TopicAlignment,
    RulingType,
    CountyToCourt,
    PersonGender,
    PersonRace,
    PartyAffiliation,
)
from datetime import date, datetime

# from dateutil.relativedelta import relativedelta
import random
from faker import Faker

# from django.db.models import Q, Count, Sum, When, FloatField
# from django.core.paginator import Paginator
# from urllib.parse import urlparse
from localflavor.us.us_states import US_STATES
from django.http import JsonResponse


def judges(request):
    """Judges landing page. Has dropdowns to find your judges."""

    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        return judges_state_county(request, state, county)

    context = {
        "msg": "Pending",
        "header": "Find your judges",
        "preamble": """Knowing your judges is important. Check them out!""",
        "states": US_STATES,
        # "radar_data": get_radar_example_data(request),
        "radar_data": get_individual_opinions_for_radar(request),
        "button_name": "Find judges",
    }

    return render(request, "judges.html", context)


def get_counties(request, state):
    """API to enable the javascript to fill the counties dropdown"""
    # based on given state, filter C2C table, return list of distinct counties
    counties = CountyToCourt.objects.filter(state=state).values_list("county", flat=True).distinct()
    return JsonResponse(list(counties), safe=False)


def judges_state_county(request, state, county):
    # grab all the tenures associated with a specific state / county
    geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)
    elections_soon = get_upcoming_elections(local_courts_list)
    tenures = Tenure.objects.filter(court__in=local_courts_list)
    courts = {}

    # iterate through all the tenures and courts associated with them
    for tenure in tenures:
        # when we get to a new court add it to the dict of courts.
        court_name = tenure.court.name
        if court_name not in courts:
            courts[court_name] = {"judges": []}
            if court_name in elections_soon:
                courts[court_name]["upcoming_election"] = True
            else:
                courts[court_name]["upcoming_election"] = False

        # For each tenure associated with a court, add it to a list in that's
        # a value in the {court: [tenure_info, tenure_info]} type dict
        courts[court_name]["judges"].append(
            {
                "name": tenure.person.name_canonical,
                "chief_justice": tenure.chief_justice,
                "party_registration": tenure.person.party_registration.title(),
                "more_info": f"/people/{tenure.person.id}/",
                "start_date": tenure.start_date,
                "end_date": tenure.end_date,
            }
        )
    context = {
        "courts": courts,
        "state": state,
        "county": county,
    }
    return render(request, "judges_state_county.html", context)


def show_person(request, person_id):
    person = Person.objects.get(id=person_id)
    tenures = Tenure.objects.filter(person=person)

    person_info = {
        "name": person.name_canonical,
        "birth_date": person.birth_date,
        "gender": person.gender,
        "race": person.race,
        "party_registration": person.party_registration.title(),
        "professional_experience": person.professional_experience,
        "law_school": person.law_school,
    }

    person_tenures = []
    for tenure in tenures:
        person_tenures.append(
            {
                "court": tenure.court.name,
                "start_date": tenure.start_date,
                "end_date": tenure.end_date,
                "selection_type": tenure.selection_type,
                "ticket_party": tenure.ticket_party,
                "appointer_name": tenure.appointer_name,
                "appointer_party": tenure.appointer_party,
                "chief_justice": tenure.chief_justice,
            }
        )

    return render(
        request,
        "person.html",
        {
            "person": person_info,
            "tenures": person_tenures,
        },
    )


def landing(request):
    """Landing page for Judgement Call users."""
    context = {
        "msg": "Welcome to Judgement Call!",
    }

    return render(request, "home.html", context)


def about(request):
    """About page, also to test if base.html is working."""
    context = {"msg": "<Insert heartfelt story about the creation of this project.>"}

    return render(request, "about.html", context)


def elections(request):
    """Elections landing page."""
    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        return elections_state_county(request, state, county)

    context = {
        "msg": "Pending",
        "header": "Elections",
        "preamble": """Informed voting is important. Please select your state
        and county to learn about any upcoming judicial elections.""",
        "states": US_STATES,
        "button_name": "Find Elections",
    }

    return render(request, "elections.html", context)


def get_candidate_info(can):
    """helper for elections_state_county"""
    # on_bench = check_incumbent(can, cour)
    return {
        "name": can.person.name_canonical,
        "party_registration": can.person.party_registration,
        "more_info": f"/people/{can.person.id}/",
        # "incumbent": on_bench,
    }


def get_upcoming_elections(relevant_courts):
    """
    Takes in QSet of courts and returns those with nearest associated election date
    """
    next_event = (
        Election.objects.filter(election_date__gte=datetime.now())
        .order_by("election_date")
        .values_list("election_date", flat=True)
        .first()
    )

    if next_event:
        return Election.objects.filter(court__in=relevant_courts, election_date=next_event)

    return Election.objects.none()


def check_incumbent(candidate, court):
    """Takes a candidate and T/F if currently sitting on election bench"""
    tenures = Tenure.objects.filter(person=candidate.person)
    been_judge = tenures.exists()
    if been_judge:
        today = datetime.now()
        on_bench = tenures.filter(court=court, start_date__lte=today, end_date__gte=today)
        if on_bench.exists():
            return (True, on_bench)
        else:
            return (False, None)
    else:
        return (False, None)


def elections_state_county(request, state, county):
    # grab all the courts associated with a specific state / county
    geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)

    # want to retrieve soonest elections
    local_elections_list = get_upcoming_elections(local_courts_list)
    elections = {
        e.court.name: {"date": e.date.strftime("%m-%d-%Y"), "type": e.court.selection_method}
        for e in local_elections_list
    }

    # link a list of candidate objects to corresponding election
    for e in local_elections_list:
        candidates = Candidacy.objects.filter(election=e)
        elections[e.court.name]["candidates"] = [get_candidate_info(c) for c in candidates]

    context = {
        "elections": elections,
        "state": state,
        "county": county,
    }

    return render(request, "elections_state_county.html", context)


def candidates(request):
    """Elections landing page."""
    context = {
        "msg": "Pending",
    }

    return render(request, "dropdown.html", context)


def analysis(request):
    """Elections landing page."""
    context = {
        "msg": "Pending!",
        "header": "Analysis",
        "preamble": "Apply filters to see judicial analytics.",
        "states": US_STATES,
        "radar_data": get_radar_example_data(request),
        "button_name": """Generate Analytics""",
    }

    return render(request, "analysis.html", context)


def add_fake_data(request):
    fake = Faker("en_US")

    # create Persons
    for _ in range(10):
        Person.objects.create(
            name_canonical=fake.name(),
            birth_date=fake.date_between(start_date="-150y", end_date="-22y"),
            gender=random.choice(PersonGender.values),
            race=random.choice(PersonRace.values),
            party_registration=random.choice(PartyAffiliation.values),
            professional_experience=fake.text(),
            law_school=fake.text(),
        )

    # create courts
    courts = [
        {
            "court_id": "ILSUP",
            "name": "Illinois Supreme Court",
            "court_level": CourtLevel.SUPREME,
            "court_type": "Supreme Court",
            "bench_size": 7,
            "selection_type": SelectionType.PARTISAN,
            "selection_method": "Partisan election with retention votes",
            "selection_jurisdiction": SelectionJurisdictionType.STATEWIDE,
            "term_length": 10,
            "url": "https://www.illinoiscourts.gov",
            "counties": [
                {"state": "IL", "county": "Cook", "fips": "17031"},
                {"state": "IL", "county": "DuPage", "fips": "17043"},
            ],
        },
        {
            "court_id": "AZSUP",
            "name": "Arizona Supreme Court",
            "court_level": CourtLevel.SUPREME,
            "court_type": "Supreme Court",
            "bench_size": 5,
            "selection_type": SelectionType.APPOINTMENT,
            "selection_method": "Merit selection with retention election",
            "selection_jurisdiction": SelectionJurisdictionType.STATEWIDE,
            "term_length": 6,
            "url": "https://www.azcourts.gov",
            "counties": [
                {"state": "AZ", "county": "Maricopa", "fips": "04013"},
                {"state": "AZ", "county": "Pima", "fips": "04019"},
            ],
        },
        {
            "court_id": "ILAPP1",
            "name": "Illinois Lower Court First District",
            "court_level": CourtLevel.LOWER,
            "court_type": "District Court of Appeal",
            "bench_size": 24,
            "selection_type": SelectionType.PARTISAN,
            "selection_jurisdiction": SelectionJurisdictionType.DISTRICT,
            "selection_method": "Partisan election with retention votes",
            "term_length": 10,
            "url": "https://www.illinoiscourts.gov",
            "counties": [
                {"state": "IL", "county": "Cook", "fips": "17031"},
            ],
        },
    ]

    for court_data in courts:
        county_list = court_data.pop("counties")
        court, _ = Court.objects.get_or_create(court_id=court_data["court_id"], defaults=court_data)
        for county_data in county_list:
            ctc, _ = CountyToCourt.objects.get_or_create(
                state=county_data["state"],
                county=county_data["county"],
                fips=county_data["fips"],
            )
            ctc.court.add(court)

    # create elections

    # make a dictionary of the courts
    court_objects = {}
    for court in Court.objects.all():
        court_objects[court.court_id] = court

    elections = [
        {
            "court": court_objects["ILSUP"],
            "election_date": date(2028, 11, 7),
        },
        {
            "court": court_objects["AZSUP"],
            "election_date": date(2028, 11, 7),
        },
        {
            "court": court_objects["ILAPP1"],
            "election_date": date(2028, 11, 7),
        },
        {
            "court": court_objects["ILSUP"],
            "election_date": date(2024, 11, 7),
        },
        {
            "court": court_objects["AZSUP"],
            "election_date": date(2024, 11, 7),
        },
        {
            "court": court_objects["ILAPP1"],
            "election_date": date(2024, 11, 7),
        },
    ]

    for election_data in elections:
        Election.objects.get_or_create(
            court=election_data["court"], election_date=election_data["election_date"]
        )

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

    tenures = list(Tenure.objects.all())
    for tenure in tenures:
        Alias.objects.get_or_create(
            alias=fake.name(),
            defaults={
                "tenure": tenure,
                "court": tenure.court,
            },
        )

    # create cases
    for _ in range(10):
        Case.objects.create(
            court=random.choice(list(Court.objects.all())),
            docket_no=fake.bothify(text="??-####"),
            case_type=random.choice(CaseType.values),
            case_title=fake.sentence(nb_words=5),
            description=fake.text(),
            decision_status=random.choice([True, False]),
            decision_outcome=random.choice(
                [
                    "Def good for justice",
                    "This one owned the libs",
                    "This one killed all the penguins",
                    "This one was about motorcycles",
                ]
            ),
            decision_date=fake.date(),
            decision_winner=random.choice(CaseParticipant.values),
            plaintiff_argument=fake.text(),
            defendant_argument=fake.text(),
            environment=random.choice(TopicAlignment.values),
            consumers=random.choice(TopicAlignment.values),
            reproductive_rights=random.choice(TopicAlignment.values),
            democratic_norms=random.choice(TopicAlignment.values),
            free_press=random.choice(TopicAlignment.values),
            public_health=random.choice(TopicAlignment.values),
            separation_church_state=random.choice(TopicAlignment.values),
            voting_access=random.choice(TopicAlignment.values),
            public_education=random.choice(TopicAlignment.values),
            free_speech=random.choice(TopicAlignment.values),
            privacy=random.choice(TopicAlignment.values),
            worker_rights=random.choice(TopicAlignment.values),
        )

    # create individual opinions
    cases = list(Case.objects.all())
    tenures = list(Tenure.objects.all())

    aliases = list(Alias.objects.all())
    for case in cases:
        opinion_writers = random.sample(aliases, k=random.randint(2, 3))
        for alias in opinion_writers:
            IndividualOpinion.objects.get_or_create(
                case=case,
                judge_alias=alias,
                defaults={"description": fake.text(), "ruling": random.choice(RulingType.values)},
            )

    return HttpResponse("Done!")


def get_individual_opinions_for_radar(
    request,
    court_id: str = "wis",
    persons: list[str] = ["Rebecca Grassl Bradley", "Jill J. Karofsky"],
):
    """
    Query multiple justices' ruling propensities to build
    Radar charts in `radar_test.html`.

    `court_id` and `person_ids` could come from judges_state_county(), but
    in any case we need all tenures in a selected court for selected
    persons.

    Returns:
        A list of lists of dicts. Each sublist represents data for a
        single justice and contains a dict like this:

            {axis:"Environment",value:0.25},

        where "axis" is the legal right in question and "value" is
        the percent of cases related to that right in which they ruled
        to protect that right.

        This format plugs right into radarChart.js for any number
        of justices and rights.
    """
    # Query all cases that had individual opinions authored by
    # (any!) tenures of the given persons in the given court.
    case_rights = ["case__" + f.name for f in Case._meta.get_fields()][-12:]
    indops = (
        IndividualOpinion.objects.filter(judge_alias__tenure__person__name_canonical__in=persons)
        .filter(case__court__court_id=court_id)
        .select_related("case")
        # .select_related("alias")
        # .select_related("tenure")
        # .select_related("person")
    ).values("judge_alias", "ruling", *case_rights)  # "case_id"

    # Transform those individual opinions into protected percentages and infringed percentages,
    # grouped by judge (person). This is "Stat option 2".
    indops_good_bad_by_judge = (
        indops.annotate(
            pro_reproductive_rights=Case_(
                When(
                    (Q(case__reproductive_rights="protected") & Q(ruling="concur"))
                    | (Q(case__reproductive_rights="infringed") & Q(ruling="dissent")),
                    then=Value(1),
                ),
                When(
                    (Q(case__reproductive_rights="infringed") & Q(ruling="concur"))
                    | (Q(case__reproductive_rights="protected") & Q(ruling="dissent")),
                    then=Value(0),
                ),
                # Defaults to None
            )
        )
        .values("judge_alias")
        .annotate(pro_reproductive_rights__avg=Avg("pro_reproductive_rights"))
    )

    # Avg() excludes `None` values by default
    # pcents_good_by_judge = indops_good_bad_by_judge.aggregate(
    #     pcent_pro_reproductive_rights=Avg("pro_reproductive_rights"),
    # )

    # return list(pcents_good_by_judge)
    return list(indops_good_bad_by_judge)
    return list(indops)


def get_radar_example_data(request):
    """
    Example view to test out D3 Radar charts in `radar_test.html`.
    Pick a court (state) and get fraction of each right type that
    involves protecting the right.

    Returns:
        A list of lists of dicts. Each sublist represents data for a
        single state and contains a dict like this:

            {axis:"Environment",value:0.25},

        where "axis" is the legal right in question and "value" is
        the percent of cases related to that right in which they ruled
        to protect that right.

        This format plugs right into radarChart.js for any number
        of courts and rights
    """
    # TODO (1): Divide by zero / null handling
    # TODO (2): Rework this to accept any number of states
    # TODO (3): After Court table join fixed, make Radar of judges
    # TODO (4): Add a legend for multiple states / judges!

    # Query only Cases in Alaska from selected rights
    test_state = "Alaska"
    test_rights = ["environment", "democratic_norms", "free_speech"]

    cases = Case.objects.filter(case_id__contains=test_state)

    resp = []
    resp.append([])
    for i, right in enumerate(test_rights):
        filter_protected_kwds = {right: "protected"}
        exclude_na_kwds = {right: "NA"}

        cases_protected = cases.filter(**filter_protected_kwds)
        cases_relevant = cases.exclude(**exclude_na_kwds)
        try:
            frac_protected = cases_protected.count() / cases_relevant.count()
        except ZeroDivisionError:
            frac_protected = 0

        resp[0].append({"axis": right, "value": frac_protected})

    return resp
