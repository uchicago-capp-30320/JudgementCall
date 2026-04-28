from django.db import models
from django.utils.translation import gettext_lazy as _
from localflavor.us.models import USStateField


# drop down types
class SelectionType(models.TextChoices):
    PARTISAN = "partisan election"
    NONPARTISAN = "nonpartisan election"
    APPOINTMENT = "appointment"


class SelectionJurisdictionType(models.TextChoices):
    STATEWIDE = "statewide"
    DISTRICT = "district"
    CIRCUIT = "circuit"


class CaseType(models.TextChoices):
    CRIMINAL = "criminal"
    CIVIL = "civil"


# provisional
class CourtLevel(models.TextChoices):
    SUPREME = "sup", _("Supreme Court")
    APPELLATE = "apl", _("Appellate Court")
    LOWER = "lwr", _("Lower Court")


class RulingType(models.TextChoices):
    CONCUR = "concur"
    DISSENT = "dissent"
    OTHER = "other"


class PartyAffiliation(models.TextChoices):
    REP = "Republican"
    DEM = "Democrat"
    IND = "Independent"
    OTHER = "Other"


class PersonGender(models.TextChoices):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class PersonRace(models.TextChoices):
    WHITE = "White"
    BLACK = "Black or African American"
    AMIN = "American Indian or Alaska Native"
    ASIAN = "Asian"
    NHPI = "Native Hawaiian or Other Pacific Islander"
    OTHER = "Other"


# Create your models here.
class Court(models.Model):
    # want to define an intelligible key for courts, eg AZSUP, ILAPP1
    court_id = models.CharField()
    name = models.CharField()
    state = USStateField()
    court_level = models.CharField(choices=CourtLevel, null=True)
    court_type = models.CharField()
    bench_size = models.IntegerField(blank=True, null=True)
    selection_type = models.CharField(
        choices=SelectionType
    )  # limit selection type to election/appointment, further explanation in selection method
    selection_method = models.TextField(blank=True)
    selection_jurisdiction = models.CharField(choices=SelectionJurisdictionType, blank=True)
    term_length = models.PositiveSmallIntegerField(blank=True, null=True)
    url = models.URLField(blank=True)
    # can add more fields from NCSC data and/or courtlistener data as needed

    def __str__(self):
        return self.name


class CountyToCourt(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    state = USStateField()
    county = models.CharField()
    fips = models.CharField()


class Person(models.Model):
    name_canonical = models.CharField()
    name_alias = models.CharField()
    birth_date = models.DateField(blank=True)
    gender = models.CharField(choices=PersonGender, blank=True)
    race = models.CharField(choices=PersonRace, blank=True)
    party_registration = models.CharField(choices=PartyAffiliation, blank=True)
    professional_experience = models.TextField(blank=True)
    law_school = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Election(models.Model):
    court = models.ForeignKey(Court, on_delete=models.PROTECT)
    date = models.DateField()

    def __str__(self):
        return f"{self.date} election for {self.court}"


class Candidacy(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)


class Tenure(models.Model):
    court = models.ForeignKey(Court, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(blank=True)
    selection_type = models.CharField(choices=SelectionType)
    ticket_party = models.CharField(choices=PartyAffiliation, blank=True)
    appointer_name = models.CharField(blank=True)
    appointer_party = models.CharField(choices=PartyAffiliation, blank=True)
    chief_justice = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.person} - {self.court}"


class Case(models.Model):
    court = models.ForeignKey(Court, on_delete=models.PROTECT)
    docket_no = models.TextField()
    case_type = models.CharField(choices=CaseType)
    case_title = models.CharField()
    description = models.TextField()
    subject_matter = models.CharField()
    pro_con = models.CharField()
    decision_status = models.BooleanField()  # whether court has issued an opinion
    decision_outcome = models.CharField(blank=True, null=True)  # opinion issued
    decision_date = models.DateField(blank=True, null=True)  # date opinion was issued

    def __str__(self):
        return self.docket_no


class IndividualOpinion(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    tenure = models.ForeignKey(Tenure, on_delete=models.CASCADE)
    description = models.TextField()
    ruling = models.CharField(choices=RulingType)
