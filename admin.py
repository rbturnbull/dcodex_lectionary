from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter

from .models import *


# Register your models here.
@admin.register(LectionaryVerse)    
class LectionaryVerseAdmin(admin.ModelAdmin):
    raw_id_fields = ("bible_verse",)
    
@admin.register(Lection)    
class LectionAdmin(admin.ModelAdmin):
    filter_horizontal = ('verses',)

admin.site.register(DayOfYear)


class LectionInSystemInline(admin.TabularInline):
    model = LectionInSystem
    extra = 0
    raw_id_fields = ("lection", "day_of_year")


@admin.register(LectionarySystem)    
class LectionarySystemAdmin(admin.ModelAdmin):
    inlines = [LectionInSystemInline]

admin.site.register(Lectionary)
