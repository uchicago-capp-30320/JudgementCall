from django.contrib import admin
from apps.judgement_call.models import (
    Court,
    Person,
    Tenure,
    Election,
    Candidacy,
    Case,
    IndividualOpinion,
)


class TenureInline(admin.TabularInline):
    model = Tenure


class ElectionInline(admin.TabularInline):
    model = Election


class IndividualOpinionInline(admin.TabularInline):
    model = IndividualOpinion


class CandidacyInline(admin.TabularInline):
    model = Candidacy


# Register your models here.
class CourtAdmin(admin.ModelAdmin):
    list_filter = ["court_level"]
    inlines = [
        ElectionInline,
        TenureInline,
    ]


admin.site.register(Court, CourtAdmin)


class PersonAdmin(admin.ModelAdmin):
    inlines = [
        TenureInline,
    ]


admin.site.register(Person, PersonAdmin)


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


class CaseAdmin(admin.ModelAdmin):
    inlines = [
        IndividualOpinionInline,
    ]


admin.site.register(Case, CaseAdmin)


class IndividualOpinionAdmin(admin.ModelAdmin):
    pass


admin.site.register(IndividualOpinion, IndividualOpinionAdmin)
