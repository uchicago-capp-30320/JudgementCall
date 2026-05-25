from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.db.models import Avg, Count, When, Value, Q
from django.db.models import Case as Case_

# from django.http import HttpResponse
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

# from django.db.models import Count, Avg
from django.db.models.functions import ExtractYear

from dateutil.relativedelta import relativedelta
import random
from faker import Faker

# from django.db.models import Q, Count, Sum, When, FloatField
# from django.core.paginator import Paginator
# from urllib.parse import urlparse
from django.urls import reverse
from localflavor.us.us_states import US_STATES
from django.http import JsonResponse
from .icons import get_judge_icons

from analysis.spacejam import make_plot as make_mds_plot

# comment to push


def judges(request):
    """Judges landing page. Has dropdowns to find your judges."""

    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        request.session["state"] = state
        request.session["county"] = county
        return judges_state_county(request, state, county)

    context = {
        "msg": "Pending",
        "header": "Find your judges",
        "preamble": """Knowing your judges is important. Check them out!""",
        "states": US_STATES,
        # "radar_data": get_radar_example_data(request),
        "radar_data": get_individual_opinions_for_radar(request),
        "button_name": "Find judges",
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "judges.html", context)


def get_counties(request, state):
    """API to enable the javascript to fill the counties dropdown"""
    # based on given state, filter C2C table, return list of distinct counties
    counties = CountyToCourt.objects.filter(state=state).values_list("county", flat=True).distinct()
    return JsonResponse(list(counties), safe=False)


def judge_sort(judge_lst):
    ordered_lst = []

    for j in judge_lst:
        if j["chief_justice"]:
            chief_j = j
        else:
            if len(ordered_lst) == 0:
                ordered_lst.append(j)
            for i, sj in enumerate(ordered_lst):
                if sj["name"] > j["name"]:
                    ordered_lst.insert((i - 1), j)

    return [chief_j] + ordered_lst


def build_court_dict(tenures, elections_soon):
    """
    build courts_dict to get list of judges & infographic
    """
    courts = {}
    # iterate through all the tenures and courts associated with them
    for tenure in tenures:
        # when we get to a new court add it to the dict of courts.
        court = tenure.court
        court_name = tenure.court.name
        if court_name not in courts:
            courts[court_name] = {"judges": [], "id": court.court_id}
            if court_name in elections_soon:
                courts[court_name]["upcoming_election"] = True
            else:
                courts[court_name]["upcoming_election"] = False

            # get demographics for the court
            court_tenures = tenures.filter(court=tenure.court)
            gender_counts = list(
                court_tenures.values("person__gender").annotate(
                    count=Count("person", distinct=True)
                )
            )
            race_counts = list(
                court_tenures.values("person__race").annotate(count=Count("person", distinct=True))
            )
            party_counts = list(
                court_tenures.values("person__party_registration").annotate(
                    count=Count("person", distinct=True)
                )
            )
            birth_years = [
                tenure.person.birth_date.year
                for tenure in court_tenures
                if tenure.person.birth_date
            ]
            if birth_years:
                avg_age = (
                    tenure.person.age
                )  # timezone.now().year - (sum(birth_years) / len(birth_years))
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
                "icons": get_judge_icons(tenure, {}),
            }
        )
    # courts[court_name]["judges"].sort(key=lambda x: x["name"])

    return courts


def judges_state_county(request, state, county):
    """
    courts structure --
    courts {
        court_name: {
            id: court_id,
            upcoming_election: T/F,
            judges: [judge1_dict, judge2_dict, judge3_dict...]
        }
    }
    """
    # grab all the tenures associated with a specific state / county
    geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
    if not geo_c2c.exists():
        raise Http404("State or county not found")
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)
    elections_soon, court_w_elections = get_upcoming_elections(local_courts_list)

    # only get current judges
    tenures = Tenure.objects.filter(
        court__in=local_courts_list, end_date__isnull=True
    ) | Tenure.objects.filter(court__in=local_courts_list, end_date__gt=timezone.now())

    courts = build_court_dict(tenures, elections_soon)

    context = {
        "courts": courts,
        "fallback_url": reverse("judgement_call:judges"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }
    return render(request, "judges_state_county.html", context)


def court_full_view(request, court_id):
    court = Court.objects.get(court_id=court_id)
    # judges = get_current_judges_for_court(court_id)
    # search by court_id to get tenures?
    # splice out helper function from judges page to make function that can
    # map over tenures
    tenures = Tenure.objects.filter(court=court, end_date__isnull=True) | Tenure.objects.filter(
        court=court, end_date__gt=timezone.now()
    )
    upcoming_elections = get_upcoming_elections([court])
    court_formatted = build_court_dict(tenures, upcoming_elections)
    details = court_formatted[court.name]
    state = request.session.get("state")
    county = request.session.get("county")

    context = {
        "court": court,
        "court_id": court_id,
        "court_formatted": court_formatted,
        "details": details,
        "gantt_data": court.gantt_json().text,
        "radar_data": [],
        # get_individual_opinions_for_radar(request, court_id=court_id, persons=judges),
        "fallback_url": reverse(
            "judgement_call:judges_state_county", kwargs={"state": state, "county": county}
        ),
    }

    return render(request, "court.html", context)


def show_person(request, person_id):
    person = get_object_or_404(Person, id=person_id)
    tenures = Tenure.objects.filter(person=person)
    indops = IndividualOpinion.objects.filter(
        judge_alias__tenure__person__name_canonical=person
    ).values(
        "description",
        "ruling",
        "case__case_title",
        "case__description",
        "case__docket_no",
        "case__case_type",
        "case__decision_date",
        "case__decision_outcome",
        "case__decision_winner",
        "case__plaintiff_argument",
        "case__defendant_argument",
        "case__document_url",
        "case__environment",
        "case__consumers",
        "case__reproductive_rights",
        "case__democratic_norms",
        "case__free_press",
        "case__public_health",
        "case__separation_church_state",
        "case__voting_access",
        "case__public_education",
        "case__free_speech",
        "case__privacy",
        "case__worker_rights",
    )

    person_info = {
        "name": person.name_canonical,
        "birth_date": person.birth_date,
        "age": person.age,
        "gender": person.gender.title(),
        "race": person.race.title(),
        "party_registration": person.party_registration.title(),
        "professional_experience": person.professional_experience.title(),
        "law_school": person.law_school.title(),
    }

    person_tenures = []
    for tenure in tenures:
        person_tenures.append(
            {
                "court": tenure.court.name,
                "start_date": tenure.start_date,
                "end_date": tenure.end_date,
                "selection_type": tenure.selection_type.title(),
                "ticket_party": tenure.ticket_party.title(),
                "appointer_name": tenure.appointer_name.title(),
                "appointer_party": tenure.appointer_party.title(),
                "chief_justice": tenure.chief_justice,
            }
        )

    def get_topics(op):
        topic_string = ", ".join(
            field.replace("_", " ").title()
            for field in Case().topic_flags()
            if op[f"case__{field}"] not in ("NA", None, "")
        )
        return topic_string

    person_opinions = []
    for op in indops:
        person_opinions.append(
            {
                "case_description": op["case__description"],
                "opinion_description": op["description"],
                "ruling": op["ruling"],
                "case_title": op["case__case_title"],
                "docket_no": op["case__docket_no"],
                "case_type": op["case__case_type"],
                "decision_date": op["case__decision_date"],
                "decision_outcome": op["case__decision_outcome"],
                "decision_winner": op["case__decision_winner"],
                "document_url": op["case__document_url"],
                "topics": get_topics(op),
            }
        )

    return render(
        request,
        "person_judge.html",
        {
            "person": person_info,
            "tenures": person_tenures,
            "opinions": person_opinions,
            "state": request.session.get("state"),
            "county": request.session.get("county"),
        },
    )


def landing(request):
    """Landing page for Judgement Call users."""

    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        request.session["state"] = state
        request.session["county"] = county

        return redirect(reverse("judgement_call:landing"))

    context = {
        "msg": "Welcome to Judgement Call!",
        "button_name": """Start Exploring""",
        "states": US_STATES,
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "home.html", context)


def methodology(request):
    """Methodology page."""
    context = {
        "msg": "<Methodology for this project.>",
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "about.html", context)


def elections(request):
    """Elections landing page."""
    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        request.session["state"] = state
        request.session["county"] = county
        return elections_state_county(request, state, county)

    context = {
        "msg": "Pending",
        "header": "Elections",
        "preamble": """Informed voting is important. Please select your state
        and county to learn about any upcoming judicial elections.""",
        "states": US_STATES,
        "button_name": "Find Elections",
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
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
        next_elections = Election.objects.filter(
            court__in=relevant_courts, election_date=next_event
        )
        next_courts = [e.court for e in next_elections]
        return (next_elections, next_courts)

    next_elections = Election.objects.none()
    next_courts = []

    return (next_elections, next_courts)


def alternate_get_elections(relevant_courts):
    """
    Takes in QSet of courts and returns those with election in next 6mo
    """
    start_date = timezone.now()
    six_mo_from_now = start_date.month + 6
    end_date = start_date + relativedelta(months=six_mo_from_now)

    upcoming_elections = Election.objects.filter(
        election_date__range=(start_date, end_date), court__in=relevant_courts
    )
    courts_w_upcoming_elections = [e.court for e in upcoming_elections]

    return (upcoming_elections, courts_w_upcoming_elections)


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
    if not geo_c2c.exists():
        raise Http404("State or county not found")
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)

    # want to retrieve soonest elections
    local_elections_list, _ = get_upcoming_elections(local_courts_list)
    elections = {
        e.court.name: {
            "date": e.election_date.strftime("%m-%d-%Y"),
            "type": e.court.selection_method.title(),
        }
        for e in local_elections_list
    }

    # link a list of candidate objects to corresponding election
    for e in local_elections_list:
        candidates = Candidacy.objects.filter(election=e)
        elections[e.court.name]["candidates"] = [get_candidate_info(c) for c in candidates]

    context = {
        "elections": elections,
        "fallback_url": reverse("judgement_call:elections"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "elections_state_county.html", context)


def candidates(request):
    """Elections landing page."""
    context = {
        "msg": "Pending",
    }

    return render(request, "dropdown.html", context)


def gantt(request):
    """Gantt chart prototype."""

    state = request.GET.get("state", "AZSUP")
    court = Court.objects.get(court_id=state)
    json = court.gantt_json()

    context = {"gantt_data": json.text, "court_id": state, "court_name": court.name}

    return render(request, "gantt.html", context)


def spacejam(request):
    """MDS chart prototype."""

    state = request.GET.get("state", "AZSUP")
    print(state)
    court = Court.objects.get(court_id=state)
    mds_data = make_mds_plot(state)

    context = {"mds_data": mds_data.to_json(), "court_id": state, "court_name": court.name}

    return render(request, "mds.html", context)


def get_current_judges_for_court(court_id):
    """
    Helper function to generate radar chart data for analysis page.
    """
    return list(
        (
            Tenure.objects.filter(court__court_id=court_id, end_date__isnull=True)
            | Tenure.objects.filter(court__court_id=court_id, end_date__gt=timezone.now())
        ).values_list("person__name_canonical", flat=True)
    )


def analysis(request):
    """Analysis landing page."""

    if request.GET.get("state") and request.GET.get("county"):
        state = request.GET["state"]
        county = request.GET["county"]
        request.session["state"] = state
        request.session["county"] = county
        return analysis_state_county(request, state, county)

    context = {
        "msg": "Pending",
        "header": "Analysis",
        "preamble": """Apply filters to see judicial analytics.""",
        "states": US_STATES,
        "button_name": "Generate Analytics",
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "analysis.html", context)


def analysis_state_county(request, state, county):
    """Analysis landing page."""

    court_id = None
    court_name = None
    gantt_data = None
    radar_data = None

    if state and county:
        geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
        if geo_c2c.exists():
            local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)
            # court = local_courts_list[0]
            court = local_courts_list.first()
            if court:
                court_id = court.court_id
                court_name = court.name
                gantt_data = court.gantt_json().text

    # use dynamic radar if court selected, fallback to example data
    if court_id:
        judges = get_current_judges_for_court(court_id)
        print("court_id:", court_id)
        print("judges:", judges)
        radar_data = get_individual_opinions_for_radar(request, court_id=court_id, persons=judges)
        print("radar_data:", radar_data)

    print("gantt_data:", gantt_data)
    print("court_name:", court_name)

    context = {
        "msg": "Pending!",
        "header": "Analysis",
        "preamble": "See judicial analytics on a national scale.",
        "states": US_STATES,
        "radar_data": radar_data,
        "button_name": """Generate Analytics""",
        # "state": court_id,
        "court_name": court_name,
        "gantt_data": gantt_data,
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "analysis_state_county.html", context)


def clear_location(request):
    request.session.pop("state", None)
    request.session.pop("county", None)
    return redirect(reverse("judgement_call:landing"))


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
                    "After working as a public defender in Phoenix for 12 "
                    "years, defending the underdog became her calling. Now on "
                    "the Arizona Superior Court, she brings a fierce "
                    "commitment to defendants' rights and has pioneered "
                    "restorative justice programs in her district.",
                    "A former jazz musician turned lawyer, he still keeps a "
                    "saxophone in his chambers and is known for making "
                    "procedural decisions with unexpected creative flair. On "
                    "the Illinois Appellate Court, he's become famous for "
                    "opinions that read like carefully composed arguments.",
                    "he spent two decades as a corporate litigator in Chicago "
                    "before realizing she wanted to serve the public good "
                    "instead of billionaires. Now presiding over family law "
                    "cases, she's developed an uncanny ability to see through "
                    "legal maneuvering to what's truly in a child's best "
                    "interest.",
                    "An immigrant from Sudan who worked his way through "
                    "law school driving a cab, he never forgot his roots in "
                    "community. On the Phoenix bench, he's known for taking "
                    "time with self-represented litigants and mentoring young "
                    "attorneys from underrepresented backgrounds.",
                    "A former investigative journalist who went to law school "
                    "at 35, she brings a reporter's eye for truth to appellate "
                    "work in Illinois. Her opinions are meticulously "
                    "researched masterpieces that have influenced criminal "
                    "justice policy statewide.",
                    "A Marine veteran and former construction worker, he "
                    "built himself up from nothing through grit and night "
                    "school. Now on the Arizona bench, he's the judge everyone "
                    "respects because they know he's earned every credential "
                    "through sacrifice.",
                    "Raised by two trial lawyers in suburban Chicago, she "
                    "practically grew up in courtrooms, but she chose a "
                    "different path as a mediator first. Her transition to "
                    "the bench brought a collaborative spirit that's "
                    "transformed how her court handles disputes.",
                    "She escaped a rough South Phoenix neighborhood through "
                    "education and returned as a legal aid attorney for 15 "
                    "years before taking the bench. Her rulings balance mercy "
                    "with accountability in ways that have made her a "
                    "lightning rod for both praise and controversy.",
                    "A Catholic seminarian-turned-lawyer who still teaches "
                    "philosophy part-time, he approaches Illinois cases with "
                    "almost theological rigor. His written decisions are dense "
                    "with legal philosophy and unexpected references to "
                    "Aquinas.",
                    "A trailblazing immigration attorney who won landmark "
                    "cases protecting asylum seekers, she was appointed to "
                    "the Arizona bench despite fierce opposition from "
                    "anti-immigration groups. Her courtroom is a battle "
                    "zone between her progressive interpretation of law and "
                    "conservative politicians trying to restrict her "
                    "authority.",
                ]
            ),
            law_school=random.choice(
                [
                    "ASU Law",
                    "University of Chicago Law School",
                    "University of Arizona Law School",
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
    # comment to commit

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

    # create alieses
    tenures = list(Tenure.objects.all())
    for tenure in tenures:
        Alias.objects.get_or_create(
            alias=random.choice([tenure.person.name_canonical, tenure.person.name_canonical[1:]]),
            defaults={
                "tenure": tenure,
                "court": tenure.court,
            },
        )

    # create cases
    for _ in range(30):
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
        opinion_writers = random.sample(aliases, k=random.randint(8, 10))
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


def get_individual_opinions_for_radar(
    request,
    court_id: str = "wis",
    persons: list[str] = ["Rebecca Grassl Bradley", "Jill J. Karofsky"],
):
    """
    Query multiple justices' ruling propensities to build
    Radar charts in `radar_test.html`.

    `court_id` and `persons` could come from judges_state_county(), but
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
    # ERROR: My query duplicates judges with multiple aliases (there are many)

    # TO REMOVE (only allow 2 judges as input at a time so
    # there is enough data overlap to build radar)
    persons = persons[-2:]

    # Query all cases that had individual opinions authored by
    # (any!) tenures of the given persons in the given court.
    case_rights = ["case__" + f.name for f in Case._meta.get_fields()][-13:-1]
    indops = (
        IndividualOpinion.objects.filter(
            judge_alias__tenure__person__name_canonical__in=persons
        ).filter(case__court__court_id=court_id)
    ).values("ruling", "judge_alias__tenure__person__name_canonical", *case_rights)

    # Transform those individual opinions into protected percentages and infringed percentages,
    # grouped by judge (person). This is "Stat option 2".
    def make_pro_right_case_when(right):
        """Helper function for converting linked IndividualOpinion data to pro/con scores"""
        kwarg_protected = {right: "protected"}
        kwarg_infringed = {right: "infringed"}

        case_when_statement = Case_(
            When(  # Ruled to protect a right, or tried stopping court from infringing
                (Q(**kwarg_protected) & Q(ruling="concur"))
                | (Q(**kwarg_infringed) & Q(ruling="dissent")),
                then=Value(1),
            ),
            When(  # Ruled to infringe on a right, or tried stopping court from protecting
                (Q(**kwarg_infringed) & Q(ruling="concur"))
                | (Q(**kwarg_protected) & Q(ruling="dissent")),
                then=Value(0),
            ),
            # Case_ defaults to None otherwise
        )

        return case_when_statement

    right_avgs_by_judge_kwargs = {
        "pro_" + case_right: make_pro_right_case_when(case_right) for case_right in case_rights
    }
    pro_right_kwargs = {
        f"pro_{case_right.replace('case__', '')}__avg": Avg(f"pro_{case_right}")
        for case_right in case_rights
    }  # Avg() helpfully excludes `None` values by default

    pro_right_avgs_by_judge = (
        indops.annotate(**right_avgs_by_judge_kwargs)
        .values("judge_alias__tenure__person__name_canonical")
        .annotate(**pro_right_kwargs)
    )

    # Convert from List of Dicts (each a judge) to List of Lists (each a judge) of Dicts.
    # TODO: Radar chart has no legend, but we will add judge name here later for that.
    # TODO: Handle missing data. What to show when Judge A is missing church-state cases,
    # and Judge B is missing free press cases? Drop both for both judges? CANNOT DEFAULT TO 0.
    # For now, drop a right (axis) if EITHER judge has not ruled on a related case
    data_for_radar = [
        [
            {
                "axis": key.replace("pro_", "").replace("__avg", "").replace("_", " "),
                "value": val,
                "name": judge_dict["judge_alias__tenure__person__name_canonical"],
            }
            for key, val in judge_dict.items()
            if key.endswith("__avg")
        ]
        for judge_dict in list(pro_right_avgs_by_judge)
    ]

    # Drop judges with no data at all
    data_for_radar = [
        judge_list
        for judge_list in data_for_radar
        if any(d["value"] is not None for d in judge_list)
    ]

    missing_axes = []
    for judge_list in data_for_radar:
        missing_axes += [
            data_dict["axis"] for data_dict in judge_list if data_dict["value"] is None
        ]
    missing_axes = set(missing_axes)

    data_for_radar_dropmissing = [
        [data_dict for data_dict in judge_list if data_dict["axis"] not in missing_axes]
        for judge_list in data_for_radar
    ]

    # print("IND OPS HERE:", data_for_radar_dropmissing[:2])
    # print(data_for_radar_dropmissing)
    return JsonResponse(data_for_radar_dropmissing, safe=False)


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
