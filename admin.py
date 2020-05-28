from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from adminsortable2.admin import SortableInlineAdminMixin

from .models import *

class LectionaryVerseMembershipInlineSortable(SortableInlineAdminMixin, admin.TabularInline):
    model = Lection.verses.through
    raw_id_fields = ("verse",)    
    extra = 0
class LectionaryVerseMembershipInline(admin.TabularInline):
    model = Lection.verses.through
    raw_id_fields = ("verse",)    
    extra = 0


# Register your models here.
@admin.register(LectionaryVerse)    
class LectionaryVerseAdmin(admin.ModelAdmin):
    raw_id_fields = ("bible_verse",)
    search_fields = ['unique_string' ]
    inlines = [LectionaryVerseMembershipInline]

@admin.register(AffiliationLections)    
class AffiliationLectionsAdmin(admin.ModelAdmin):
    model = AffiliationLections
    
@admin.register(Lection)    
class LectionAdmin(admin.ModelAdmin):
    filter_horizontal = ('verses',)
    search_fields = ['description']  
#    inlines = [LectionaryVerseMembershipInline]
    inlines = [LectionaryVerseMembershipInlineSortable]
 

admin.site.register(DayOfYear)
admin.site.register(FixedDate)


class LectionInSystemInline(admin.TabularInline):
    model = LectionInSystem
    extra = 0
    raw_id_fields = ("lection", "day_of_year", "fixed_date", 'reference_membership')



class LectionInSystemInlineSortable(SortableInlineAdminMixin, admin.TabularInline):
    model = LectionarySystem.lections.through
    extra = 0
    raw_id_fields = ("lection", "day_of_year", "fixed_date", 'reference_membership')

@admin.register(LectionInSystem)    
class LectionInSystemAdmin(admin.ModelAdmin):
    search_fields = ['order', 'lection__id', 'fixed_date__id' ]


@admin.register(LectionarySystem)    
class LectionarySystemAdmin(admin.ModelAdmin):
#    inlines = [LectionInSystemInline]
    inlines = [LectionInSystemInlineSortable]

admin.site.register(Lectionary)
