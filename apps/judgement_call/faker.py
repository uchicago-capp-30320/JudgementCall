from faker import Faker
import random
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
from django.http import HttpResponse
from datetime import date

def add_fake_data():
    """Create fake data to use while building Judgement Call"""
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