from django.test import TestCase
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
    Person,
    Tenure,
    Election,
    Candidacy,
    Alias,
    Case,
    IndividualOpinion,
    SelectionType,
    SelectionJurisdictionType,
    CaseType,
    CaseParticipant,
    TopicAlignment,
    CourtLevel,
    RulingType,
    PartyAffiliation,
    PersonGender,
    PersonRace,
)
from .icons import get_judge_icons
from datetime import date, timedelta
from utils.matching import standardize_alias
from django.urls import reverse


class HomepageTestCase(TestCase):
    """Tests for the homepage"""

    def test_home_page_returns_200(self):
        """Make sure the homepage loads"""
        response = self.client.get("")
        assert response.status_code == 200

    def test_home_page_correct_buttons(self):
        """Make sure the homepage has the right stuff on it"""
        response = self.client.get("")
        assert "Start Exploring" in response.content.decode()

    def test_home_page_loads_buttons_with_state_info(self):
        """Ensure the 3 buttons appear if you have the state info"""
        response = self.client.get("/?state=IL&county=Cook", follow=True)
        assert "Your Judges" in response.content.decode()


class JudgesTestCase(TestCase):
    """Tests for the judge / court lookup page"""

    def test_judges_page_returns_200(self):
        """Make sure the landing page loads"""
        response = self.client.get("/judges/")
        assert response.status_code == 200

    def test_judges_page_has_states(self):
        """Make sure the states are populating in our dropdowns"""
        response = self.client.get("/judges/")
        assert "states" in response.context
        assert len(response.context["states"]) > 0


class JudgesStateCountyTestCase(TestCase):
    """Tests for the specific state county judge view"""

    def setUp(self):
        # create a court
        court = Court.objects.create(
            court_id="ILAPP1",
            name="Illinois Lower Court First District",
            court_level=CourtLevel.LOWER,
            court_type="District Court of Appeal",
            bench_size=24,
            selection_type=SelectionType.PARTISAN,
            selection_jurisdiction=SelectionJurisdictionType.DISTRICT,
            selection_method="Partisan Election With Retention Votes",
            term_length=10,
            url="https://www.illinoiscourts.gov",
        )

        # create a CountyToCourt + add it to the join table
        c2c = CountyToCourt.objects.create(state="IL", county="Cook", fips="17031")
        c2c.court.add(court)

        # create a Person
        self.person1 = Person.objects.create(
            name_canonical="Joey Baga-Donuts",
            birth_date=date(1980, 5, 15),  # May 15, 1980
            gender=PersonGender.MALE,
            race=PersonRace.BLACK,
            party_registration=PartyAffiliation.DEM,
            professional_experience="Big law baby. Before that worked in gov.",
            law_school="UCLA",
        )

        # create a second Person
        self.person2 = Person.objects.create(
            name_canonical="Jackie Potatohead",
            birth_date=date(1965, 5, 15),  # May 15, 1980
            gender=PersonGender.FEMALE,
            race=PersonRace.WHITE,
            party_registration=PartyAffiliation.REP,
            professional_experience="Social worker",
            law_school="Penn",
        )

        # create four tenures, two for Joey two for Jackie
        Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

        # this tenure is in the past
        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() - timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

    def test_judges_state_county_returns_200(self):
        """Test judge state county page returns ok"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)
        assert response.status_code == 200

    def test_judges_page_sends_to_judges_state_county(self):
        """Make sure dropdown submit sends us to judges_state_county"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)

        # check that it has the right data
        assert "courts" in response.context
        assert response.context["state"] == "IL"
        assert response.context["county"] == "Cook"

    def test_judges_state_county_returns_404(self):
        """Test judge state county page returns ok"""
        response = self.client.get("/judges/?state=XY&county=Gobble", follow=True)
        assert response.status_code == 404

    def test_judges_are_all_current(self):
        """Only judges with current tenures should appear"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)
        # Joey has 2 current tenures, Jackie has 1 = 3 total tenure entries
        assert len(response.context["courts"]["Illinois Lower Court First District"]["judges"]) == 3

    def test_person_page_ok(self):
        """Test whether the person page generates ok"""
        response = self.client.get(f"/people/{self.person1.id}/")
        assert response.status_code == 200

    def test_more_details_person(self):
        """Make sure person page has name and details"""
        response = self.client.get(f"/people/{self.person1.id}/")
        assert response.context["person"]["name"] == "Joey Baga-Donuts"

    def test_more_details_nonexistent_judge(self):
        """Try a url for a nonexistent judge id sends a 404"""
        response = self.client.get("/people/1000000000000/")
        assert response.status_code == 404

    def test_demographics_in_quick_stats(self):
        """Make sure the quick stats are generating the correct age
        don't double count one person even if they have multiple tenures"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)
        courts = response.context["courts"]
        court_data = courts["Illinois Lower Court First District"]

        # Check average age
        assert court_data["avg_age"] == 51

        # Check gender counts (1 male, 1 female)
        gender_data = {item["person__gender"]: item["count"] for item in court_data["gender_data"]}
        assert gender_data["m"] == 1
        assert gender_data["f"] == 1

        # Check race counts (1 black, 1 white)
        race_data = {item["person__race"]: item["count"] for item in court_data["race_data"]}
        assert race_data["black or african american"] == 1
        assert race_data["white"] == 1

        # Check party counts (1 dem, 1 rep)
        party_data = {
            item["person__party_registration"]: item["count"] for item in court_data["party_data"]
        }
        assert party_data["democrat"] == 1
        assert party_data["republican"] == 1


class CourtFullViewTestCase(TestCase):
    """Tests the court demography, sitting judge, timeline and issue radar page"""

    def setUp(self):
        # create a court
        court = Court.objects.create(
            court_id="ILAPP1",
            name="Illinois Lower Court First District",
            court_level=CourtLevel.LOWER,
            court_type="District Court of Appeal",
            bench_size=24,
            selection_type=SelectionType.PARTISAN,
            selection_jurisdiction=SelectionJurisdictionType.DISTRICT,
            selection_method="Partisan Election With Retention Votes",
            term_length=10,
            url="https://www.illinoiscourts.gov",
        )

        # create a CountyToCourt + add it to the join table
        c2c = CountyToCourt.objects.create(state="IL", county="Cook", fips="17031")
        c2c.court.add(court)

        # create a Person
        self.person1 = Person.objects.create(
            name_canonical="Joey Baga-Donuts",
            birth_date=date(1980, 5, 15),  # May 15, 1980
            gender=PersonGender.MALE,
            race=PersonRace.BLACK,
            party_registration=PartyAffiliation.DEM,
            professional_experience="Big law baby. Before that worked in gov.",
            law_school="UCLA",
        )

        # create a second Person
        self.person2 = Person.objects.create(
            name_canonical="Jackie Potatohead",
            birth_date=date(1965, 5, 15),  # May 15, 1980
            gender=PersonGender.FEMALE,
            race=PersonRace.WHITE,
            party_registration=PartyAffiliation.REP,
            professional_experience="Social worker",
            law_school="Penn",
        )

        # create four tenures, two for Joey two for Jackie
        self.tenure1 = Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

        # this tenure is in the past
        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() - timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

        # add a case with topics
        case = Case.objects.create(
            court=court,
            docket_no="2024-001",
            case_type=CaseType.CIVIL_RIGHTS,
            case_title="Test Case",
            description="A test case",
            decision_status=True,
            decision_outcome="plaintiff",
            decision_date=date.today(),
            environment="NA",
            consumers="protected",  # Joey ruled to protect consumers
            reproductive_rights="NA",
            democratic_norms="NA",
            free_press="NA",
            public_health="NA",
            separation_church_state="NA",
            voting_access="NA",
            public_education="NA",
            free_speech="NA",
            privacy="protected",  # Joey ruled to protect privacy
            worker_rights="NA",
        )

        # add an alias
        alias = Alias.objects.create(alias="Joey Baga-Donuts", tenure=self.tenure1, court=court)

        # add individual opinions
        IndividualOpinion.objects.create(
            case=case,
            judge_alias=alias,
            description="Concurred with majority",
            ruling=RulingType.CONCUR,
        )

    def test_court_view_redirects_if_no_session_established(self):
        """Without state/county in the session, redirect to landing"""
        response = self.client.get("/judges/ILAPP1/")
        assert response.status_code == 302
        assert response.url == "/"

    def test_court_demographics(self):
        """Make sure the court demographics are correct"""
        # start the session
        self.client.get("/?state=IL&county=Cook")

        # hit the court full view page
        response = self.client.get("/judges/ILAPP1/", follow=True)
        details = response.context["details"]

        # Check average age
        assert details["avg_age"] == 51

        # Check gender counts (1 male, 1 female)
        gender_data = {item["person__gender"]: item["count"] for item in details["gender_data"]}
        assert gender_data["m"] == 1
        assert gender_data["f"] == 1

        # Check race counts (1 black, 1 white)
        race_data = {item["person__race"]: item["count"] for item in details["race_data"]}
        assert race_data["black or african american"] == 1
        assert race_data["white"] == 1

        # Check party counts (1 dem, 1 rep)
        party_data = {
            item["person__party_registration"]: item["count"] for item in details["party_data"]
        }
        assert party_data["democrat"] == 1
        assert party_data["republican"] == 1

    def test_judge_icons(self):
        """Test that judge icons match the case rulings"""
        # start the session
        self.client.get("/?state=IL&county=Cook")

        # hit the view
        response = self.client.get("/judges/ILAPP1", follow=True)
        details = response.context["details"]

        # Get first judge's icons
        first_judge = details["judges"][0]
        icons = first_judge["icons"]

        # make sure the icons are right
        assert "wallet" in icons
        assert "eye_tracking" in icons

        # make sure the icons are the right color, grey for not enough cases
        assert icons["wallet"][1] == "#808080ff"  # bc not enough cases to decide
        assert icons["eye_tracking"][1] == "#808080ff"


class ElectionsTestCase(TestCase):
    """Tests for the election lookup page"""

    def test_elections_page_returns_200(self):
        """Make sure the elections landing page loads"""
        response = self.client.get("/elections/")
        assert response.status_code == 200

    def test_judges_page_has_states(self):
        """Make sure the states are populating in our dropdowns"""
        response = self.client.get("/elections/")
        assert "states" in response.context
        assert len(response.context["states"]) > 0


class ElectionsStateCountyTestCase(TestCase):
    """Test for specific state county elections view"""

    def setUp(self):
        # create a court
        court = Court.objects.create(
            court_id="ILAPP1",
            name="Illinois Lower Court First District",
            court_level=CourtLevel.LOWER,
            court_type="District Court of Appeal",
            bench_size=24,
            selection_type=SelectionType.PARTISAN,
            selection_jurisdiction=SelectionJurisdictionType.DISTRICT,
            selection_method="Partisan Election With Retention Votes",
            term_length=10,
            url="https://www.illinoiscourts.gov",
        )

        # create a CountyToCourt + add it to the join table
        c2c = CountyToCourt.objects.create(state="IL", county="Cook", fips="17031")
        c2c.court.add(court)

        # create a Person
        self.person1 = Person.objects.create(
            name_canonical="Joey Baga-Donuts",
            birth_date=date(1980, 5, 15),  # May 15, 1980
            gender=PersonGender.MALE,
            race=PersonRace.BLACK,
            party_registration=PartyAffiliation.DEM,
            professional_experience="Big law baby. Before that worked in gov.",
            law_school="UCLA",
        )

        # create a second Person
        self.person2 = Person.objects.create(
            name_canonical="Jackie Potatohead",
            birth_date=date(1985, 5, 15),  # May 15, 1980
            gender=PersonGender.FEMALE,
            race=PersonRace.WHITE,
            party_registration=PartyAffiliation.REP,
            professional_experience="Social worker",
            law_school="Penn",
        )

        # create three tenures, two for Joey one for Jackie
        tenure1 = Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person1,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() + timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

        # this tenure is in the past
        Tenure.objects.create(
            court=court,
            person=self.person2,
            start_date=date.today() - timedelta(days=365 * 15),
            end_date=date.today() - timedelta(days=100),
            selection_type=SelectionType.NONPARTISAN,
            ticket_party=PartyAffiliation.DEM,
            chief_justice=True,
        )

        election = Election.objects.create(
            court=court,
            election_id="IL-COOK-2026",
            election_date=date.today() + timedelta(days=90),
            incumbent=tenure1,
        )

        Candidacy.objects.create(person=self.person1, election=election)
        Candidacy.objects.create(person=self.person2, election=election)

    def test_elections_state_county_returns_200(self):
        """Make sure the elections landing page loads"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        assert response.status_code == 200

    def test_elections_state_county_returns_404_for_fake_state(self):
        """Make sure the elections landing page doesn't load if bad entry"""
        response = self.client.get("/elections/?state=XY&county=Bokchoy", follow=True)
        assert response.status_code == 404

    def test_upcoming_election_shows_up(self):
        """Make sure the elections landing page loads"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        assert "Illinois Lower Court First District" in response.content.decode()

    def test_elections_state_county_shows_candidates(self):
        """Test that the candidates appear for the election"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        elections = response.context["elections"]
        illinois_election = elections["IL-COOK-2026"]
        candidates = illinois_election["candidates"]
        candidate_names = [c["name"] for c in candidates]
        assert "Jackie Potatohead" in candidate_names

    def test_elections_shows_election_date(self):
        """Make sure the election date appears for each election"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        elections = response.context["elections"]
        illinois_election = elections["IL-COOK-2026"]
        assert illinois_election["date"] == (date.today() + timedelta(days=90)).strftime("%m-%d-%Y")

    def test_elections_shows_election_type(self):
        """Make sure the election date appears for each election"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        elections = response.context["elections"]
        illinois_election = elections["IL-COOK-2026"]
        assert illinois_election["type"] == "Partisan Election With Retention Votes"

    def test_candidate_more_details_link(self):
        """Make sure the details link on candidates leads to valid person page"""
        response = self.client.get("/elections/?state=IL&county=Cook", follow=True)
        elections = response.context["elections"]
        illinois_election = elections["IL-COOK-2026"]
        candidates = illinois_election["candidates"]
        for candidate in candidates:
            candidate_link = candidate["more_info"]
            person_response = self.client.get(candidate_link, follow=True)
            assert person_response.status_code == 200


class AnalysisTestCase(TestCase):
    """Tests for the analysis lookup page"""

    def test_analysis_page_returns_200(self):
        """Make sure the analysis landing page loads"""
        response = self.client.get("/analysis/")
        assert response.status_code == 200

    # def test_judges_page_has_states(self):
    #     """Make sure the states are populating in our dropdowns"""
    #     response = self.client.get("/analysis/")
    #     assert "states" in response.context
    #     assert len(response.context["states"]) > 0


class MatchingTestCase(TestCase):
    """Tests for the matching.py util"""

    def setUp(self):
        # create some aliases
        self.aliases = [
            "Chief Justice John Barbenheimer C.J.",
            "Roberta Presiding Justice P.J.",
            "Sandra Connor BY DESIGNATION A.R.J.",
        ]

    def test_standardize_alias_ending_key_words(self):
        """Make sure the standardize_alias function removes the ending from alias"""
        fixed_aliases = []
        for alias in self.aliases:
            fixed = standardize_alias(alias)
            fixed_aliases.append(fixed)

        combined = " ".join(fixed_aliases)

        assert "C.J." not in combined
        assert "c.j." not in combined
        assert "cj" not in combined
        assert "Chief Justice" not in combined
        assert "chief justice" not in combined
        assert "Justice" not in combined
        assert "justice" not in combined
        assert "Presiding" not in combined
        assert "presiding" not in combined
        assert "P.J." not in combined
        assert "PJ" not in combined
        assert "pj" not in combined
        assert "p.j." not in combined
        assert "by designation" not in combined
        assert "BY DESIGNATION" not in combined
