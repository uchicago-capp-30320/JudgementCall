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
from datetime import date


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
            selection_method="Partisan election with retention votes",
            term_length=10,
            url="https://www.illinoiscourts.gov",
        )

        # create a CountyToCourt + add it to the join table
        c2c = CountyToCourt.objects.create(state="IL", county="Cook", fips="17031")
        c2c.court.add(court)

        # create a Person
        self.person = Person.objects.create(
            name_canonical="Joey Baga-Donuts",
            birth_date=date(1980, 5, 15),  # May 15, 1980
            gender=PersonGender.MALE,
            race=PersonRace.BLACK,
            party_registration=PartyAffiliation.DEM,
            professional_experience="Big law baby. Before that worked in gov.",
            law_school="UCLA",
        )

        # create a Tenure
        Tenure.objects.create(
            court=court,
            person=self.person,
            start_date=date(2015, 2, 10),
            end_date=date(2030, 2, 10),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

        Tenure.objects.create(
            court=court,
            person=self.person,
            start_date=date(2015, 2, 10),
            end_date=date(2025, 2, 10),
            selection_type=SelectionType.PARTISAN,
            ticket_party=PartyAffiliation.DEM,
            appointer_name="",
            appointer_party="",
            chief_justice=False,
        )

    def test_judges_page_sends_to_judges_state_county(self):
        """Make sure dropdown submit sends us to judges_state_county"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)

        # check that it successfully redirects
        assert response.status_code == 200

        # check that it has the right data
        assert "courts" in response.context
        assert response.context["state"] == "IL"
        assert response.context["county"] == "Cook"

    def test_judges_state_county_returns_200(self):
        """Test judge state county page returns ok"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)
        assert response.status_code == 200

    def test_judges_state_county_returns_404(self):
        """Test judge state county page returns ok"""
        response = self.client.get("/judges/?state=XY&county=Gobble", follow=True)
        assert response.status_code == 404

    def test_judges_are_all_current(self):
        """Only judges with no end date or end_date in the future should appear"""
        response = self.client.get("/judges/?state=IL&county=Cook", follow=True)
        assert len(response.context["courts"]["Illinois Lower Court First District"]["judges"]) == 1

    def test_person_page_ok(self):
        """Test whether the person page generates ok"""
        response = self.client.get("/people/1/")
        assert response.status_code == 200

    def test_more_details_person(self):
        """Make sure person page has name and details"""
        response = self.client.get(f"/people/{self.person.id}/")
        assert response.context["person"]["name"] == "Joey Baga-Donuts"

    def test_more_details_nonexistent_judge(self):
        """Try a url for a nonexistent judge id sends a 404"""
        response = self.client.get("/people/8/")
        assert response.status_code == 404
