from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
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
from django.utils import timezone
from django.db.models import Count, Avg
from django.db.models.functions import ExtractYear

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
    if not geo_c2c.exists():
        raise Http404("State or county not found")
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)
    elections_soon = get_upcoming_elections(local_courts_list)

    # only get current judges
    tenures = Tenure.objects.filter(
        court__in=local_courts_list, end_date__isnull=True
    ) | Tenure.objects.filter(court__in=local_courts_list, end_date__gt=timezone.now())
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

            # get demographics for the court
            court_tenures = tenures.filter(court=tenure.court)
            gender_counts = list(court_tenures.values("person__gender").annotate(count=Count("id")))
            race_counts = list(court_tenures.values("person__race").annotate(count=Count("id")))
            party_counts = list(
                court_tenures.values("person__party_registration").annotate(count=Count("id"))
            )
            birth_years = [
                tenure.person.birth_date.year
                for tenure in court_tenures
                if tenure.person.birth_date
            ]
            if birth_years:
                avg_age = timezone.now().year - (sum(birth_years) / len(birth_years))
            else:
                avg_age = None

            # for each court, add the demographic data
            courts[court_name]["gender_data"] = [
                item for item in gender_counts if item["person__gender"] is not None
            ]
            courts[court_name]["race_data"] = [
                item for item in race_counts if item["person__race"] is not None
            ]
            courts[court_name]["party_data"] = [
                item for item in party_counts if item["person__party_registration"] is not None
            ]
            courts[court_name]["avg_age"] = avg_age

        # For each tenure associated with a court, add it to a list that's
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
    person = get_object_or_404(Person, id=person_id)
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
    for _ in range(30):
        Person.objects.create(
            name_canonical=fake.name(),
            birth_date=fake.date_between(start_date="-70y", end_date="-22y"),
            gender=random.choice(PersonGender.values),
            race=random.choice(PersonRace.values),
            party_registration=random.choice(PartyAffiliation.values),
            professional_experience=random.choice(
                [
                    "After working as a public defender in Phoenix for 12 years, defending the underdog became her calling. Now on the Arizona Superior Court, she brings a fierce commitment to defendants' rights and has pioneered restorative justice programs in her district.",
                    "A former jazz musician turned lawyer, he still keeps a saxophone in his chambers and is known for making procedural decisions with unexpected creative flair. On the Illinois Appellate Court, he's become famous for opinions that read like carefully composed arguments.",
                    "he spent two decades as a corporate litigator in Chicago before realizing she wanted to serve the public good instead of billionaires. Now presiding over family law cases, she's developed an uncanny ability to see through legal maneuvering to what's truly in a child's best interest.",
                    "An immigrant from Sudan who worked his way through law school driving a cab, he never forgot his roots in community. On the Phoenix bench, he's known for taking time with self-represented litigants and mentoring young attorneys from underrepresented backgrounds.",
                    "A former investigative journalist who went to law school at 35, she brings a reporter's eye for truth to appellate work in Illinois. Her opinions are meticulously researched masterpieces that have influenced criminal justice policy statewide.",
                    "A Marine veteran and former construction worker, he built himself up from nothing through grit and night school. Now on the Arizona bench, he's the judge everyone respects because they know he's earned every credential through sacrifice.",
                    "Raised by two trial lawyers in suburban Chicago, she practically grew up in courtrooms, but she chose a different path as a mediator first. Her transition to the bench brought a collaborative spirit that's transformed how her court handles disputes.",
                    "She escaped a rough South Phoenix neighborhood through education and returned as a legal aid attorney for 15 years before taking the bench. Her rulings balance mercy with accountability in ways that have made her a lightning rod for both praise and controversy.",
                    "A Catholic seminarian-turned-lawyer who still teaches philosophy part-time, he approaches Illinois cases with almost theological rigor. His written decisions are dense with legal philosophy and unexpected references to Aquinas.",
                    "A trailblazing immigration attorney who won landmark cases protecting asylum seekers, she was appointed to the Arizona bench despite fierce opposition from anti-immigration groups. Her courtroom is a battle zone between her progressive interpretation of law and conservative politicians trying to restrict her authority.",
                ]
            ),
            law_school=random.choice(
                [
                    "ASU Law",
                    "University of Chicago Law SchoolUniversity of Arizona Law School",
                    "Penn Carey Law",
                ]
            ),
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
        Election.objects.get_or_create(
            court=election_data["court"], election_date=election_data["date"]
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
            start = fake.date_between(start_date=date(1990, 1, 1), end_date=date(2026, 1, 1))
            end = fake.date_between(start_date=start, end_date=date(2040, 1, 1))
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
    for _ in range(400):
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
                defaults={
                    "description": fake.text(),
                    "ruling": random.choices(
                        [RulingType.CONCUR, RulingType.DISSENT, RulingType.OTHER],
                        weights=[70, 28, 2],
                        k=1,
                    )[0],
                },
            )

    return HttpResponse("Done!")


def get_individual_opinions_for_radar(request):
    """
    Query multiple justices' ruling propensities to test out D3
    Radar charts in `radar_test.html`

    Returns:
        A list of lists of dicts. Each sublist represents data for a
        single justice and contains a dict like this:

            {axis:"Environment",value:0.25},

        where "axis" is the legal right in question and "value" is
        the percent of cases related to that right in which they ruled
        to protect that right.

        This format plugs right into radarChart.js for any number
        of justices and rights
    """
    # Query only IndividualOpinions in a single state from justices X and Y
    pass


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
    # Need to unpack dict to query Django by variable-named columns

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

    # resp_example = [
    #     [ # This list corresponds to one Case
    #         {"axis": "made", "value": 0.1}, # This dict corresponds to one right
    #         {"axis": "up", "value": 0.123},
    #         {"axis": "also made up", "value": 0.90},
    #     ]
    # ]
