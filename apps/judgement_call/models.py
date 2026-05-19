from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import date
from localflavor.us.models import USStateField
from django.db import connection
import pandas as pd
from jellyfish import jaro_winkler_similarity
from string import punctuation


# drop down types
class SelectionType(models.TextChoices):
    PARTISAN = "partisan election"
    NONPARTISAN = "nonpartisan election"
    APPOINTMENT = "appointment"
    RETENTION = "retention election"
    LEGISLATURE = "elected by legislature"


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
    REP = "republican"
    DEM = "democrat"
    IND = "independent"
    OTHER = "other"


class PersonGender(models.TextChoices):
    MALE = "m"
    FEMALE = "f"
    OTHER = "o"


class PersonRace(models.TextChoices):
    WHITE = "white"
    BLACK = "black or african american"
    AMIN = "american indian or alaska native"
    ASIAN = "asian"
    NHPI = "native hawaiian or other pacific islander"
    OTHER = "other"


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
    court = models.ManyToManyField(Court)
    state = USStateField()
    county = models.CharField()
    fips = models.CharField()

    def __str__(self):
        rep_str = f"{self.county} - "
        for court in self.court.all():
            rep_str = rep_str + f"{court.name}"
        return rep_str


class Person(models.Model):
    name_canonical = models.CharField()
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(choices=PersonGender, blank=True, null=True)
    race = models.CharField(choices=PersonRace, blank=True, null=True)
    party_registration = models.CharField(choices=PartyAffiliation, blank=True, null=True)
    professional_experience = models.TextField(blank=True)
    law_school = models.TextField(blank=True)

    def __str__(self):
        return self.name_canonical

    @property
    def age(self):
        if self.birth_date.year == 3000:
            return None
        else:
            return years_since(self.birth_date)

    @property
    def current_tenure(self):
        tenures = Tenure.objects.filter(
            person=self, start_date__lte=date.today(), end_date__gte=date.today()
        )
        if len(tenures) > 1:
            print("Warning! Current tenure lookup returned multiple tenures.")
        return tenures


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

    @property
    def tenure_length_to_date(self):
        if self.start_date.year == 3000:
            return None
        return years_since(self.start_date)

    @property
    def tenure_length_remaining(self):
        if self.end_date.year == 3000:
            return None
        return years_to(self.end_date)


class Election(models.Model):
    court = models.ForeignKey(Court, on_delete=models.PROTECT)
    election_date = models.DateField()
    incumbent = models.ForeignKey(Tenure, on_delete=models.PROTECT, null=True, blank=True)

    def deduce_elections(self):
        court_elections = Tenure.objects.values("id", "court_id", "end_date")
        election_df = pd.DataFrame(list(court_elections))

        for index, row in election_df.iterrows():
            tenure = Tenure.objects.get(pk=row["id"])
            court = Court.objects.get(pk=row["court_id"])
            term_end = row["end_date"]
            elect_date = term_end.replace(year=term_end.year - 1, month=11, day=5)
            Election.objects.create(court=court, election_date=elect_date, incumbent=tenure)

    def __str__(self):
        return f"{self.election_date} election for {self.court}"


class Candidacy(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Candidacies"


class Alias(models.Model):
    alias = models.CharField()
    # manual linking of alias to tenure
    tenure = models.ForeignKey(Tenure, on_delete=models.PROTECT, blank=True, null=True)
    # the court the case which generated the alias came from
    court = models.ForeignKey(Court, on_delete=models.PROTECT)

    @property
    def matched(self):
        return self.tenure is not None

    def find_matches(self, alias=None) -> list[Tenure]:
        if not alias:
            alias = self.alias
        court_tenures = Tenure.objects.filter(court=self.court)
        matches = {}
        for tenure in court_tenures:
            name = self.standardize_name(tenure.person.name_canonical)
            matches[tenure] = jaro_winkler_similarity(alias, name)
        return matches

    def match_tenure(self, update=False):
        print(f"before: alias {self.alias}, tenure {self.tenure}")
        if not update:
            if self.matched:
                return self.tenure
        matches = self.find_matches()
        if matches == {}:
            print(f"No names found: does {self.court} exist?")
            return self.tenure
        top_match = max(matches, key=lambda k: matches[k])
        print(f"best match: {top_match}, {matches[top_match]}")
        if matches[top_match] > 0.9:
            # setting tenure to the top match
            self.tenure = top_match
            self.save()
        else:
            try_alias = self.alias.replace("justice", "").replace(" j ", " ")
            try_alias = try_alias.replace("senior", "").replace("chief", "")
            if try_alias != self.alias:
                print(f"rerunning with {try_alias}")
                matches = self.find_matches(try_alias)
                top_match = max(matches, key=lambda k: matches[k])
                print(f"best match: {top_match}, {matches[top_match]}")
                if matches[top_match] > 0.9:
                    # setting tenure to the top match
                    self.tenure = top_match
                    self.save()

        print(f"after: alias {self.alias}, tenure {self.tenure}")
        return self.tenure

    @staticmethod
    def standardize_name(name: str):
        return name.strip().lower().translate(str.maketrans("", "", punctuation))

    class Meta:
        verbose_name_plural = "Aliases"

    def __str__(self):
        return f"{self.tenure}: {self.alias} ({self.court})"


class Case(models.Model):
    case_id = models.CharField(null=True)
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
        return f"{self.case_title} /{self.docket_no}, {self.court}"


class IndividualOpinion(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    # alias comes directly from case data; connects to tenure via alias table
    judge_alias = models.ForeignKey(Alias, on_delete=models.PROTECT, null=True)
    description = models.TextField()
    ruling = models.CharField(choices=RulingType)

    def __str__(self):
        return f"{self.judge_alias} - {self.case}"


# Helper methods for calculating year diffs
def years_since(date_field):
    years_since = round((date.today() - date_field).days / 365.25)
    if years_since < 0:
        raise ValueError("date is not in the past!")
    return years_since


def years_to(date_field):
    years_to = round((date_field - date.today()).days / 365.25)
    if years_to < 0:
        raise ValueError("date is not in the future!")
    return years_to
