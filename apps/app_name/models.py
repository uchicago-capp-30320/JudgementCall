from django.db import models
from django.utils.translation import gettext_lazy as _


# drop down types
class SelectionType(models.TextChoices):
    PARTISAN = "partisan election"
    NONPARTISAN = "nonpartisan election"
    APPOINTMENT = "appointment"


class CaseType(models.TextChoices):
    CRIM = "criminal"
    CIVIL = "civil"


# provisional
class CourtType(models.TextChoices):
    SUPREME = "sup", _("Supreme Court")
    APPELLATE = "apl", _("Appellate Court")
    LOWER = "lwr", _("Lower Court")


class PartyAffiliation(models.TextChoices):
    REP = "Republican"
    DEM = "Democrat"
    IND = "Independent"
    OTHER = "Other"


# Create your models here.
class Court(models.Model):
    # want to define an intelligible key for courts, eg AZSUP, ILAPP1
    org_id = models.CharField(primary_key=True)
    name = models.CharField()
    court_type = models.CharField(choices=CourtType)
    bench_size = models.IntegerField(blank=True)
    selection_type = models.CharField(
        choices=SelectionType
    )  # limit selection type to election/appointment, further explanation in selection method
    selection_method = models.TextField(blank=True)
    term_length = models.PositiveSmallIntegerField(choices=range(20), blank=True)
    url = models.URLField(blank=True)
    # can add more fields from NCSC data and/or courtlistener data as needed

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.TextField()
    birth_date = models.DateField(blank=True)
    gender = models.CharField(blank=True)
    race = models.CharField(blank=True)
    party_registration = models.CharField(choices=PartyAffiliation, blank=True)
    professional_experience = models.TextField()

    def __str__(self):
        return self.name


class Election(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"{self.date} election for {self.court}"


class Candidacy(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)


class Tenure(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
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
    docket_no = models.TextField()
    case_type = models.TextChoices()
    case_title = models.CharField()
    description = models.TextField()
    pro_con = models.CharField()
    decision_status = models.BooleanField()
    decision_outcome = models.CharField()

    def __str__(self):
        return self.docket_no


class IndividualOpinion(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    tenure = models.ForeignKey(Tenure, on_delete=models.CASCADE)
    description = models.TextField()
