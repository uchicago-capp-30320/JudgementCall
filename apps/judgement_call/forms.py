from django import forms
from apps.judgement_call.models import Court, Case

POLITICAL_DIMENSIONS = [field.name for field in Case._meta.get_fields()][14:-2]
DIMENSION_CHOICES = [("", "Overall Polarization")] + [
    (dim, dim.replace("_", " ").title()) for dim in POLITICAL_DIMENSIONS
]


class ChoroplethForm(forms.Form):
    dimension = forms.ChoiceField(
        choices=DIMENSION_CHOICES,
        required=False,
        help_text="",
    )
