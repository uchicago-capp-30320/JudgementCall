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


# Register your models here.
class CourtAdmin(admin.ModelAdmin):
    pass


admin.site.register(Court, CourtAdmin)


class PersonAdmin(admin.ModelAdmin):
    pass


admin.site.register(Person, PersonAdmin)


class TenureAdmin(admin.ModelAdmin):
    pass


admin.site.register(Tenure, TenureAdmin)


class ElectionAdmin(admin.ModelAdmin):
    pass


admin.site.register(Election, ElectionAdmin)


class CandidacyAdmin(admin.ModelAdmin):
    pass


admin.site.register(Candidacy, CandidacyAdmin)


class CaseAdmin(admin.ModelAdmin):
    pass


admin.site.register(Case, CaseAdmin)


class IndividualOpinionAdmin(admin.ModelAdmin):
    pass


admin.site.register(IndividualOpinion, IndividualOpinionAdmin)
