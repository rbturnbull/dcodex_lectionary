from django.db import models
from django.db.models import Max, Min
from dcodex.models import Manuscript, Verse
from dcodex_bible.models import BibleVerse
import logging

class DayOfYear(models.Model):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    
    DAY_CHOICES = [
        (SUNDAY, 'Sunday'),
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
    ]
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    
    EASTER = 'E'
    PENTECOST = 'P'
    FEAST_OF_THE_CROSS = 'F'
    LENT = 'L'
    GREAT_WEEK = 'G'
    
    PERIOD_CHOICES = [
        (EASTER, 'Easter'),
        (PENTECOST, 'Pentecost'),
        (FEAST_OF_THE_CROSS, 'Feast of the Cross'),
        (LENT, 'Lent'),
        (GREAT_WEEK, 'Great Week'),
    ]
    period = models.CharField(max_length=1, choices=PERIOD_CHOICES)
    
    week = models.CharField(max_length=15)
    weekday_number = models.CharField(max_length=32)    
    earliest_date = models.CharField(max_length=15) 
    latest_date = models.CharField(max_length=15) 
    description = models.CharField(max_length=64)
    def __str__(self):
        string = "%s: %s" % (self.get_period_display(), self.get_day_of_week_display() )
        if self.week.isdigit():
            string += ", Week %s" % (self.week )
        elif self.week != "Holy Week":
            string += ", %s" % (self.week )        
        
        return string
    class Meta:
        verbose_name_plural = 'Days of year'

class Lection(models.Model):
    day_of_year = models.ForeignKey(DayOfYear, on_delete=models.CASCADE)
    book = models.CharField(max_length=16)
    passage_description = models.CharField(max_length=32)
    
    def __str__(self):
        return "%s %s %s" % (self.day_of_year.__str__(), self.book, self.passage_description )
class LectionaryVerse(Verse):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE)
    bible_verse = models.ForeignKey(BibleVerse, on_delete=models.CASCADE)
    def weight(self):
        return self.bible_verse.weight()
    
    def reference(self, abbreviation = False, end_verse=None):    
        if end_verse != None:
            return self.bible_verse.reference( abbreviation=abbreviation, end_verse=end_verse.bible_verse )
        return self.bible_verse.reference( abbreviation=abbreviation )
class LectionVerseSpan(models.Model):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE)
    start_verse = models.ForeignKey(LectionaryVerse, on_delete=models.CASCADE, related_name='LectionVerseSpan_start_verse', blank=True, null=True, default=None)
    end_verse   = models.ForeignKey(LectionaryVerse, on_delete=models.CASCADE, related_name='LectionVerseSpan_end_verse', blank=True, null=True, default=None)
    
    def __str__(self):
        return "%s on %s" % (self.start_verse.reference(abbreviation=True, end_verse=self.end_verse), self.lection.__str__() )