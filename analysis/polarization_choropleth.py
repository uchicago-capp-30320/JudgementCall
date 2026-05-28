from django.db.models import Avg, When, Value, FloatField, Case as Django_Case
import pandas as pd
import plotly.express as px
from sklearn.metrics.pairwise import nan_euclidean_distances
from sklearn.manifold import MDS

from apps.judgement_call.models import Court, CountyToCourt, Case


def produce_data(court_type: str = "Supreme Court", geo_unit: str = "state"):
    # Calculating the percentage of times each court is protecting a political
    # dimension.
    political_dimensions = Case.topic_flags()
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

    output_df = pd.DataFrame(output)

    # Calculating eudlidean distances between each court, then using
    # multi-dimensional scaling to create a single list of values indicating
    # polarization.
    dist = nan_euclidean_distances(output_df.iloc[:, 1 : output_df.shape[1] - 1])
    embedding = MDS(n_components=1, n_init=1, init="random", metric="precomputed")
    transformed = pd.Series(embedding.fit_transform(dist).reshape(1, len(output_df))[0])
    output_df.insert(len(output_df.columns), "polarity", transformed)

    return output_df


def create_choropleth(map_data: pd.DataFrame, dimension: str = None, geo_unit: str = "state"):
    # Creating choropleth
    if dimension is not None:
        fig = px.choropleth(
            map_data,
            locations=geo_unit,
            locationmode="USA-states",
            scope="usa",
            color=dimension,
            color_continuous_scale="Spectral",
        )
    else:
        fig = px.choropleth(
            map_data,
            locations=geo_unit,
            locationmode="USA-states",
            scope="usa",
            color="polarity",
            color_continuous_scale="Spectral",
        )

    return fig
