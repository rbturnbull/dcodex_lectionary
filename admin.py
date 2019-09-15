from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter

from .models import *


# Register your models here.
class LectionVerseSpanInline(admin.TabularInline):
    model = LectionVerseSpan
    extra = 0
    raw_id_fields = ("start_verse","end_verse")
    
@admin.register(Lection)    
class LectionAdmin(admin.ModelAdmin):
    inlines = [LectionVerseSpanInline]
admin.site.register(DayOfYear)

#admin.site.register(Lection)
#admin.site.register(LectionVerseSpan)
