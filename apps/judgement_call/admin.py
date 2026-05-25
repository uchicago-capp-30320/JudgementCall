from django.contrib import admin
from apps.judgement_call.models import (
    Court,
    CountyToCourt,
    Person,
    Tenure,
    Alias,
    Election,
    Candidacy,
    CaseProcessingRun,
    Case,
    IndividualOpinion,
)


class TenureInline(admin.TabularInline):
    model = Tenure


class ElectionInline(admin.TabularInline):
    model = Election


class IndividualOpinionInline(admin.TabularInline):
    model = IndividualOpinion
    # lots of aliases, each requring joins for the __str__
    # this makes the dropdowns in this table require exponential joins
    raw_id_fields = ["judge_alias"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "judge_alias__tenure__person",
                "judge_alias__tenure__court",
                "judge_alias__court",
            )
        )


class CandidacyInline(admin.TabularInline):
    model = Candidacy


class CaseInline(admin.TabularInline):
    model = Case


# Register your models here.
class CourtAdmin(admin.ModelAdmin):
    list_filter = ["court_level"]
    inlines = [
        ElectionInline,
        TenureInline,
    ]


admin.site.register(Court, CourtAdmin)


class CountyToCourtAdmin(admin.ModelAdmin):
    pass


admin.site.register(CountyToCourt, CountyToCourtAdmin)


class PersonAdmin(admin.ModelAdmin):
    inlines = [
        TenureInline,
    ]


admin.site.register(Person, PersonAdmin)


class AliasAdmin(admin.ModelAdmin):
    list_filter = ["court"]


admin.site.register(Alias, AliasAdmin)


class TenureAdmin(admin.ModelAdmin):
    pass


admin.site.register(Tenure, TenureAdmin)


class ElectionAdmin(admin.ModelAdmin):
    inlines = [
        CandidacyInline,
    ]


admin.site.register(Election, ElectionAdmin)


class CandidacyAdmin(admin.ModelAdmin):
    pass


admin.site.register(Candidacy, CandidacyAdmin)


class CaseProcessingRunAdmin(admin.ModelAdmin):
    inlines = [
        CaseInline,
    ]


admin.site.register(CaseProcessingRun, CaseProcessingRunAdmin)


class CaseAdmin(admin.ModelAdmin):
    inlines = [
        IndividualOpinionInline,
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "individualopinion_set__judge_alias__tenure__person",
                "individualopinion_set__judge_alias__tenure__court",
                "individualopinion_set__judge_alias__court",
            )
        )


admin.site.register(Case, CaseAdmin)


class IndividualOpinionAdmin(admin.ModelAdmin):
    pass


admin.site.register(IndividualOpinion, IndividualOpinionAdmin)
