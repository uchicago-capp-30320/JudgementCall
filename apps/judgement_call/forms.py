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


def get_court_choices():
    return [("", "--- Select a Court ---")] + [
        (c.court_id, c.name)
        for c in Court.objects.filter(court_type="Supreme Court").order_by("name")
    ]


class SpacejamForm(forms.Form):
    state = forms.ChoiceField(choices=[], label="Court")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["state"].choices = get_court_choices()
