from django import forms
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

STATE_CHOICES = [("AZ", "Arizona"), ("CA", "California"), ...]  # or pull from a model
COURT_LEVEL_CHOICES = [("supreme", "Supreme Court"), ("appellate", "Appellate"), ...]


class ChoroplethForm(forms.Form):
    state = forms.ChoiceField(choices=STATE_CHOICES)
    court_level = forms.ChoiceField(choices=COURT_LEVEL_CHOICES)
    issue_dimension = forms.CharField()
    geounit = forms.ChoiceField(choices=STATE_CHOICES)  # same or different list
