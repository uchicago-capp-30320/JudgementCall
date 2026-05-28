from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
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
    CountyToCourt,
)
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.http import JsonResponse
from datetime import datetime
from localflavor.us.us_states import US_STATES
import re
from .icons import get_judge_icons, get_topic_icons
from apps.judgement_call.forms import ChoroplethForm, SpacejamForm
from analysis.polarization_choropleth import produce_data, create_choropleth
from analysis.spacejam import make_plot as make_mds_plot


def judges(request):
    """
    Original judges landing page. Has dropdowns to get state and county for
    customized judge viewing.
    """
    # redirect to custom view upon receiving state/county
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
        "button_name": "Find judges",
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "judges.html", context)


def get_counties(request, state):
    """API to enable the JavaScript to fill out the counties dropdown."""
    # based on given state, filter C2C table, return list of distinct counties
    counties = (
        CountyToCourt.objects.filter(state=state)
        .values_list("county", flat=True)
        .order_by("county")
        .distinct()
    )
    return JsonResponse(list(counties), safe=False)


def judge_sort(judge_lst):
    """
    Sorts list of judge dictionaries alphabetically with Chief Justice coming
    first.
    """
    ordered_lst = []

    for j in judge_lst:
        # pick out chief justice to add later
        if j["chief_justice"]:
            chief_j = j
        else:
            for i, sj in enumerate(ordered_lst):
                if sj["name"] > j["name"]:
                    ordered_lst.insert(i, j)
                    break
            else:
                ordered_lst.append(j)

    return [chief_j] + ordered_lst


def build_court_dict(tenures, elections_courts):
    """
    Build courts dictionary used in judge_state_county and full_court_view to
    create judge cards and court demography infographic.
    """
    courts = {}
    # iterate through all the tenures and courts associated with them
    for tenure in tenures:
        # when we get to a new court add it to the dict of courts.
        court = tenure.court
        court_name = tenure.court.name
        if court_name not in courts:
            courts[court_name] = {"judges": [], "id": court.court_id}
            # courts with upcoming elections
            upcoming_courts = [c.name for c in elections_courts]
            if court_name in upcoming_courts:
                # turns on upcoming election flag
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
                "icons": get_judge_icons(tenure, {}),
            }
        )

    # sort judges by chief justice then alphabetically
    for court in courts.keys():
        courts[court]["judges"] = judge_sort(courts[court]["judges"])

    return courts


def judges_state_county(request, state, county):
    """
    Take state and county to identify relevant tenures. Tenures are used to
    generate courts dictionary to populate judges quick view.
    """
    # grab all the tenures associated with a specific state / county
    geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
    if not geo_c2c.exists():
        raise Http404("State or county not found")
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)
    _, court_w_elections = get_upcoming_elections(local_courts_list)

    # only get current judges
    tenures = Tenure.objects.filter(
        court__in=local_courts_list, end_date__isnull=True
    ) | Tenure.objects.filter(court__in=local_courts_list, end_date__gt=timezone.now())

    courts = build_court_dict(tenures, court_w_elections)

    context = {
        "courts": courts,
        "fallback_url": reverse("judgement_call:judges"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }
    return render(request, "judges_state_county.html", context)


def court_full_view(request, court_id):
    """
    Creates detailed court-level analytics view with infographic, judge listings,
    tenure, and ruling compatibility radar chart.
    """
    # retrieve relevant court
    court = Court.objects.get(court_id=court_id)
    # retrieve tenures to build court dict
    tenures = Tenure.objects.filter(court=court, end_date__isnull=True) | Tenure.objects.filter(
        court=court, end_date__gt=timezone.now()
    )
    _, upcoming_courts = get_upcoming_elections([court])
    court_formatted = build_court_dict(tenures, upcoming_courts)
    # for this view we only need the one court
    details = court_formatted[court.name]

    # some weird string handling with states/counties
    if request.session.get("state") and request.session.get("county"):
        state = request.session.get("state").strip(
            "()',",
        )
        county = request.session.get("county").strip("()',")
    else:
        # redirect to initial dropdown if no sessions geodata
        return redirect("judgement_call:landing")

    context = {
        "court": court,
        "court_id": court_id,
        "court_formatted": court_formatted,
        "details": details,
        "gantt_data": court.gantt_json().text,
        "radar_data": [],
        "state": state,
        "county": county,
        "fallback_url": reverse(
            "judgement_call:judges_state_county", kwargs={"state": state, "county": county}
        ),
    }
    return render(request, "court.html", context)


def show_person(request, person_id):
    """
    Detailed view for an individual judge or person.
    """
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
        topics_dict = {
            field.replace("_", " ").title(): op[f"case__{field}"]
            for field in Case().topic_flags()
            if op[f"case__{field}"] not in ("NA", None, "")
        }
        topics_string = ", ".join(topics_dict.keys())
        return topics_string, topics_dict

    person_opinions = []
    for op in indops:
        topics_string, topics_dict = get_topics(op)
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
                "topics_string": topics_string,
                "topics_dict": topics_dict,
            }
        )

    return render(
        request,
        "person_judge.html",
        {
            "person": person_info,
            "tenures": person_tenures,
            "topic_icons": get_topic_icons(person),
            "opinions": person_opinions,
            "state": request.session.get("state"),
            "county": request.session.get("county"),
        },
    )


def landing(request):
    """
    Landing page for Judgement Call users. If no sessions data, populates
    dropdown prompting them to select their state and county.
    """

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


def about(request):
    """Team about page."""
    context = {
        "msg": "<About for this project.>",
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "about.html", context)


def methodology(request):
    """Methodology page."""
    context = {
        "msg": "<Methodology for this project.>",
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "methodology.html", context)


def elections(request):
    """
    Original elections landing page. Has dropdowns to get state and county for
    customized elections viewing.
    """
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


def quick_name_tidy(name):
    """
    Regex implementation to reformat candidates whose party affiliations
    accidentally got scraped in with their names. Returns name and party
    separated.
    """
    pattern = r"\s*(\(D\)|\(R\)|\(Nonpartisan\))"
    parts = re.split(pattern, name)
    cleaned = [p.strip() for p in parts if p]

    if cleaned[1] == "(R)" or cleaned[0] == "(Republican)":
        clean_party = "Republican"
    elif cleaned[1] == "(D)" or cleaned[0] == "(Democrat)":
        clean_party = "Democrat"
    else:
        clean_party = "Nonpartisan"
    clean_name = cleaned[0]

    return clean_name, clean_party


def get_candidate_info(can):
    """
    I forget, honestly
    """
    name = can.person.name_canonical
    if name.endswith("(R)") or name.endswith("(D)") or name.endswith("Nonpartisan"):
        name, party = quick_name_tidy(name)
    else:
        party = can.person.party_registration

    has_tenures = Tenure.objects.filter(person=can.person).exists()

    info = {
        "name": name,
        "party_registration": party,
    }

    # only include the link if they are a judge
    if has_tenures:
        info["more_info"] = f"/people/{can.person.id}/"

    return info


def get_upcoming_elections(relevant_courts):
    """
    Takes QSet of courts, looks at soonest election date, returns courts from
    QSet that have an election on that soonest election date.
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
    Takes in QSet of courts and returns those with election in next 6 months.
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
    """
    Takes a candidate and T/F if currently sitting on election bench.
    Intended to be used in elections page to signal retention elections.
    """
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
    """
    Custom elections summary view based on state and county.
    """
    # grab all the courts associated with a specific state / county
    geo_c2c = CountyToCourt.objects.filter(state=state, county=county)
    if not geo_c2c.exists():
        raise Http404("State or county not found")
    local_courts_list = Court.objects.filter(countytocourt__in=geo_c2c)

    # want to retrieve soonest elections
    local_elections_list, _ = get_upcoming_elections(local_courts_list)
    elections = {
        e.election_id: {
            "court_name": e.court.name,
            "date": e.election_date.strftime("%m-%d-%Y"),
            "type": e.court.selection_method.title(),
        }
        for e in local_elections_list
    }

    # link a list of candidate objects to corresponding election
    for e in local_elections_list:
        candidates = Candidacy.objects.filter(election=e)
        elections[e.election_id]["candidates"] = [get_candidate_info(c) for c in candidates]

    context = {
        "elections": elections,
        "fallback_url": reverse("judgement_call:elections"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "elections_state_county.html", context)


def gantt(request):
    """Gantt chart implemented on courts view."""

    state = request.GET.get("state", "AZSUP")
    court = Court.objects.get(court_id=state)
    json = court.gantt_json()

    context = {"gantt_data": json.text, "court_id": state, "court_name": court.name}

    return render(request, "gantt.html", context)


def spacejam(request):
    """
    Multidimensional Scaling chart implemented on Analysis page with dropdown
    form.
    """
    mds_data_json = None
    court_name = None
    form = SpacejamForm(request.GET if "state" in request.GET else None)

    if form and form.is_valid():
        court_id = form.cleaned_data["state"]
        court = Court.objects.get(court_id=court_id)
        court_name = court.name
        mds_data = make_mds_plot(court_id)
        mds_data_json = mds_data.to_json() if mds_data is not None else None

    context = {
        "form": form,
        "mds_data": mds_data_json,
        "court_name": court_name,
        "state": request.session.get("state"),
        "county": request.session.get("county"),
        "fallback_url": reverse("judgement_call:analysis"),
    }
    return render(request, "spacejam.html", context)


def spacejam_backup(request):
    """Old spacejam view. Can still see raw chart at /spacejam_backup/<courtid>"""

    court_id = request.GET.get("state", "AZSUP")
    court = Court.objects.get(court_id=court_id)
    mds_data = make_mds_plot(court_id)
    mds_data_json = mds_data.to_json() if mds_data is not None else None

    context = {"mds_data": mds_data_json, "court_id": court_id, "court_name": court.name}

    return render(request, "mds.html", context)


def get_current_judges_for_court(court_id):
    """
    Helper function to list of judges for radar chart.
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
        "preamble": """Please explore our visualizations exploring high-level
        judicial analytics.""",
        "states": US_STATES,
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "analysis.html", context)


def get_choropleth(request):
    """
    Helper function that uses form input to generate dynamic Plotly polarization
    chart output.
    """

    chart_html = None
    if "dimension" in request.GET:
        form = ChoroplethForm(request.GET)
    else:
        form = ChoroplethForm()

    if form.is_valid():
        court_type = "Supreme Court"
        geo_unit = "state"
        dimension = form.cleaned_data["dimension"] or None

        df = produce_data(court_type=court_type, geo_unit=geo_unit)
        fig = create_choropleth(map_data=df, dimension=dimension, geo_unit=geo_unit)
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return {"form": form, "chart_html": chart_html}


def polarization(request):
    """
    Gets choropleth data and pushes to polarization template.
    """
    choro_dict = get_choropleth(request)
    context = {
        "state": request.session.get("state"),
        "county": request.session.get("county"),
        "choropleth_form": choro_dict["form"],
        "chart_html": choro_dict["chart_html"],
        "header": "State Supreme Court Issues Polarization Map",
        "preamble": """Select an issue area to see polarization state-level court decisions.""",
        "fallback_url": reverse("judgement_call:analysis"),
    }
    return render(request, "polarization.html", context)


def analysis_state_county(request, state, county):
    """
    Old version of analysis view that assumed radar and gantt charts would be
    on the analysis page.
    """

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
        radar_data = get_individual_opinions_for_radar(request, court_id=court_id, persons=judges)
        print("radar_data:", radar_data)

    context = {
        "msg": "Pending!",
        "header": "Analysis",
        "preamble": "See judicial analytics on a national scale.",
        "states": US_STATES,
        "radar_data": [],
        "button_name": """Generate Analytics""",
        "court_name": court_name,
        "gantt_data": gantt_data,
        "fallback_url": reverse("judgement_call:landing"),
        "state": request.session.get("state"),
        "county": request.session.get("county"),
    }

    return render(request, "analysis_state_county.html", context)


def candidates(request):
    """Elections landing page."""
    context = {
        "msg": "Pending",
    }

    return render(request, "dropdown.html", context)


def clear_location(request):
    """
    Clears location cache and redirects user to dropdown landing to select new
    location.
    """
    request.session.pop("state", None)
    request.session.pop("county", None)
    return redirect(reverse("judgement_call:landing"))


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
    Older prototype version of radar chart.

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
