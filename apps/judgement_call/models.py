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
    CIVIL_RIGHTS = "Civil Rights"
    GOV_STRUCTURE = "Government Structure"
    ECON_LABOR = "Economic and Labor Rights"
    VOTING_ELECTIONS = "Voting Rights and Elections"
    CRIMINAL_LAW = "Criminal Law"
    ENVIRONMENT = "Environment"
    JUDICIAL_SELECTION = "Judicial Selection and Administration"
    EDUCATION = "Education"
    SPEECH_RELIGION = "Speech and Religion"
    DUE_PROCESS = "Civil Due Process"
    REPRODUCTIVE_RIGHTS = "Reproductive Rights"
    TORTS = "Torts and Liability"
    JUDICIAL_INTERPRETATION = "Judicial Interpretation"
    ELECTION2024 = "Election 2024"


class CaseParticipant(models.TextChoices):
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    OTHER = "other"


class TopicAlignment(models.TextChoices):
    PROTECTED = "protected"
    INFRINGED = "infringed"
    NA = "NA"


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
    court_id = models.CharField()
    name = models.CharField()
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


class Alias(models.Model):
    alias = models.CharField()
    # manual linking of alias to tenure
    tenure = models.ForeignKey(Tenure, on_delete=models.PROTECT, blank=True, null=True)
    # the court the case which generated the alias came from
    court = models.ForeignKey(Court, on_delete=models.PROTECT)


class Case(models.Model):
    court = models.ForeignKey(Court, on_delete=models.PROTECT)
    docket_no = models.CharField()
    case_type = models.CharField(choices=CaseType, blank=True, null=True)
    case_title = models.CharField()
    description = models.TextField()
    decision_status = models.BooleanField(default=True)  # whether court has issued an opinion
    decision_outcome = models.CharField(blank=True, null=True)  # opinion issued
    decision_date = models.DateField(blank=True, null=True)  # date opinion was issued
    # added 4/30:
    decision_winner = models.CharField(choices=CaseParticipant, blank=True, null=True)
    plaintiff_argument = models.TextField(blank=True, null=True)
    defendant_argument = models.TextField(blank=True, null=True)
    # topic flags
    environment = models.CharField(choices=TopicAlignment, blank=True)
    consumers = models.CharField(choices=TopicAlignment, blank=True)
    reproductive_rights = models.CharField(choices=TopicAlignment, blank=True)
    democratic_norms = models.CharField(choices=TopicAlignment, blank=True)
    free_press = models.CharField(choices=TopicAlignment, blank=True)
    public_health = models.CharField(choices=TopicAlignment, blank=True)
    separation_church_state = models.CharField(choices=TopicAlignment, blank=True)
    voting_access = models.CharField(choices=TopicAlignment, blank=True)
    public_education = models.CharField(choices=TopicAlignment, blank=True)
    free_speech = models.CharField(choices=TopicAlignment, blank=True)
    privacy = models.CharField(choices=TopicAlignment, blank=True)
    worker_rights = models.CharField(choices=TopicAlignment, blank=True)

    def __str__(self):
        return self.docket_no


class IndividualOpinion(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    # alias comes directly from case data; connects to tenure via alias table
    judge_alias = models.ForeignKey(Alias, on_delete=models.PROTECT)
    description = models.TextField()
    ruling = models.CharField(choices=RulingType)
