from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminMixin, SortableAdminBase

from dcodex.admin import ManuscriptChildAdmin
from .models import *


class LectionaryDayChildAdmin(PolymorphicChildModelAdmin):
    """ Base admin class for all LectionaryDay models """
    base_model = LectionaryDay  # Optional, explicitly set here.


@admin.register(MiscDay)
class MiscDayAdmin(LectionaryDayChildAdmin):
    base_model = MiscDay
    show_in_index = True


@admin.register(EothinaDay)
class EothinaDayAdmin(LectionaryDayChildAdmin):
    base_model = EothinaDay
    show_in_index = True


@admin.register(FixedDay)
class FixedDayAdmin(LectionaryDayChildAdmin):
    base_model = FixedDay
    show_in_index = True


@admin.register(MovableDay)
class MovableDayAdmin(SortableAdminMixin, LectionaryDayChildAdmin):
    base_model = MovableDay
    show_in_index = True
    list_per_page = 200


@admin.register(LectionaryDay)
class LectionaryDayParentAdmin(PolymorphicParentModelAdmin):
    """ The parent LectionaryDay admin """
    base_model = LectionaryDay  # Optional, explicitly set here.
    child_models = (MovableDay, FixedDay, EothinaDay, MiscDay)
    list_filter = (PolymorphicChildModelFilter,)  # This is optional.


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
class LectionAdmin(SortableAdminBase, admin.ModelAdmin):
    filter_horizontal = ('verses',)
    search_fields = ['description']  
#    inlines = [LectionaryVerseMembershipInline]
    inlines = [LectionaryVerseMembershipInlineSortable]
 
admin.site.register(AffiliationLectionarySystem)
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
class LectionarySystemAdmin(SortableAdminBase, admin.ModelAdmin):
#    inlines = [LectionInSystemInline]
    inlines = [LectionInSystemInlineSortable]


@admin.register(Lectionary)    
class LectionaryAdmin(ManuscriptChildAdmin):
    pass
