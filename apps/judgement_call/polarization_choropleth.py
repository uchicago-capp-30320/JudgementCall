from django.db.models import Avg, When, Value, FloatField, Case as Django_Case
import pandas as pd
import plotly.express as px
from sklearn.metrics.pairwise import nan_euclidean_distances
from sklearn.manifold import MDS

from apps.judgement_call.models import Court, CountyToCourt, Case


def polarity_choropleth(court_type: str = "Supreme Court", geo_unit: str = "state"):
    # Calculating the percentage of times each court is protecting a political
    # dimension.
    political_dimensions = [field.name for field in Case._meta.get_fields()][14:]
    annotator = {}
    for dim in political_dimensions:
        annotator[dim] = (
            Avg(
                Django_Case(
                    When(**{dim: "protected"}, then=Value(1)),
                    When(**{dim: "infringed"}, then=Value(0)),
                    default=None,
                    output_field=FloatField(),
                )
            )
            * 100
        )

    # Filtering the query for a given court type.
    output = list(
        Case.objects.filter(court__court_type=court_type).values("court_id").annotate(**annotator)
    )

    # Linking court ids to geographic units and creating data necessary for
    # choropleth.
    courts = list(
        Court.objects.values("id", f"countytocourt__{geo_unit}")
        .filter(court_type=court_type)
        .distinct()
    )
    geo_courts = {court["id"]: court[f"countytocourt__{geo_unit}"] for court in courts}

    for court in output:
        court[geo_unit] = geo_courts[court["court_id"]]

    choropleth_data = pd.DataFrame(output)

    # Calculating eudlidean distances between each court, then using
    # multi-dimensional scaling to create a single list of values indicating
    # polarization.
    dist = nan_euclidean_distances(choropleth_data.iloc[:, 1 : choropleth_data.shape[1] - 1])
    embedding = MDS(n_components=1, n_init=1, init="random", metric="precomputed")
    transformed = list(embedding.fit_transform(dist).reshape(1, 3)[0])
    map_data = pd.DataFrame(
        {
            "court_id": choropleth_data["court_id"],
            "transformed_euclidean_distances": transformed,
            geo_unit: choropleth_data[geo_unit],
        }
    )

    # Creating choropleth
    fig = px.choropleth(
        map_data,
        locations=geo_unit,
        locationmode="USA-states",
        scope="usa",
        color="transformed_euclidean_distances",
        color_continuous_scale="Viridis_r",
    )

    return fig
