from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from .models import DataSet, Publisher, Region, DataSetFile
from urllib.parse import urlparse


def landing(request):
    """Landing page for Judgement Call users."""
    context = {
        "msg": "Welcome to Judgement Call!",
    }

    return render(request, "home.html", context)
