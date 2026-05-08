from django.db import models
from django.utils.translation import gettext_lazy as _
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
    court = models.ManyToManyField(Court)
    state = USStateField()
    county = models.CharField()
    fips = models.CharField()


class Person(models.Model):
    name_canonical = models.CharField()
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

    class Meta:
        verbose_name_plural = "Candidacies"


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

    def match_names(self) -> pd.DataFrame:
        """
        Retrieves the alias and court_ids from the Alias table, retrieves
        the canon names and the court_ids from the Tenure table. Turns them
        both into dataframes and performs a matching algorithm on them.
        """
        # Retrieving aliases
        query = """
            SELECT
                alias,
                court_id
            FROM
                judgement_call_alias
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        aliases = pd.DataFrame(
            {"name": [res[0] for res in results], "court_id": [res[1] for res in results]}
        )

        # Retrieving canon names
        canon_names = {"name": [], "court_id": []}
        for court_id in aliases["court_id"].unique():
            query = """
                SELECT p.name_canonical, c.id
                FROM
                    judgement_call_person as p,
                    judgement_call_court as c,
                    judgement_call_tenure as t
                WHERE
                    c.id = t.court_id
                    AND
                    p.id = t.person_id
                    AND
                    c.id = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(query, [court_id])
                results = cursor.fetchall()

                canon_names["name"] += [res[0] for res in results]
                canon_names["court_id"] += [res[1] for res in results]

        return Alias.run_matching(canon_names, aliases)

    def update_matches(self):
        """
        Main function that creates a matching output, and uses the output
        to update tenure in the Alias table in the database.
        """
        match_table = self.match_names()
        num_matches = len(match_table)

        query_get = """
            SELECT
                t.id
            FROM
                judgement_call_tenure as t,
                judgement_call_person as p
            WHERE
                t.person_id = p.id
                AND
                p.name_canonical = %s
                AND
                t.court_id = %s
            LIMIT 1
        """

        query_update = """
            UPDATE
                judgement_call_alias
            SET
                tenure_id = %s
            WHERE
                alias = %s
                AND
                court_id = %s
        """

        for row_num in range(num_matches):
            with connection.cursor() as cursor:
                query_inputs = [match_table.loc[row_num, "name"], self.court_id]
                cursor.execute(query_get, query_inputs)
                result = cursor.fetchall()

                if not result:
                    print(f"No tenure found for {match_table.loc[row_num, 'name']}")
                    continue

                query_inputs = [result[0][0], match_table.loc[row_num, "alias"], self.court_id]
                cursor.execute(query_update, query_inputs)

    @staticmethod
    def match(names: pd.DataFrame, aliases: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a dataframe with canonical names, and a dataframe with aliases.
        Iterates through each alias, standardizes it, and calculates its
        Jaro-Winkler similary score against every standardized canonical name.

        It identifies the highest scoring canonical name match, and gives a match
        quality rating.

        Returns a pandas dataframe with every unique alias given in the alias
        input dataframe, along with its found match, and the match quality.
        """
        r_table = {"alias": [], "name": [], "match_quality": []}

        unique_aliases = aliases["name"].unique()
        num_aliases = len(unique_aliases)
        for num in range(num_aliases):
            alias = aliases.loc[num, "name"]
            # Alias standardizing happens in ingest.py now
            r_table["alias"].append(alias)

            num_names = len(names)

            matching_table = {"name": list(names["name"]), "match_score": []}

            for i in range(num_names):
                name = names.loc[i, "name"].lower().replace("\n", "")
                name = "".join(ch for ch in name if ch not in punctuation)
                score = jaro_winkler_similarity(alias, name)
                matching_table["match_score"].append(score)

            top_match = (
                pd.DataFrame(matching_table).sort_values(by="match_score", ascending=False).iloc[0]
            )
            match_name = top_match["name"]
            r_table["name"].append(match_name)
            match_score = top_match["match_score"]

            if match_score >= 0.9:
                r_table["match_quality"].append("High")
            elif (match_score < 0.9) and (match_score >= 0.5):
                r_table["match_quality"].append("Medium")
            else:
                r_table["match_quality"].append("Low")

        r_table = pd.DataFrame(r_table)
        return r_table[r_table["match_quality"] == "High"]

    @staticmethod
    def run_matching(names: pd.DataFrame, alias: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a dataframe with canonical names, and a dataframe with aliases. Function
        iterates through each state (or court) and runs the match() function on them
        returning a dataframe of unique aliases with their matches and match quality.
        """
        unique_cids = names["court_id"].unique()

        r_list = []

        for court_id in unique_cids:
            print(f"Matching names for {court_id}")
            court_names = names[names["court_id"] == court_id].reset_index(drop=True)
            court_aliases = alias[alias["court_id"] == court_id].reset_index(drop=True)

            match_results = Alias.match(court_names, court_aliases)

            r_list.append(match_results)

        return pd.concat(r_list)

    class Meta:
        verbose_name_plural = "Aliases"

    def __str__(self):
        return f"{self.alias} ({self.court})"


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
    judge_alias = models.ForeignKey(Alias, on_delete=models.PROTECT, null=True)
    description = models.TextField()
    ruling = models.CharField(choices=RulingType)
