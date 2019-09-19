from django.db import models
from django.db.models import Max, Min
from dcodex.models import Manuscript, Verse
from dcodex_bible.models import BibleVerse
from django.shortcuts import render


import logging

class LectionaryVerse(Verse):
    bible_verse = models.ForeignKey(BibleVerse, on_delete=models.CASCADE)
    
    def bible_reference( self, abbrevation = False ):
        return self.bible_verse.reference( abbrevation )
    
    def bible_reference_abbreviation( self ):
        return self.bible_verse.reference_abbreviation( )
    
    def reference(self, abbreviation = False, end_verse=None):
        if end_verse:
            return "vv %d–%d" % (self.id, end_verse.id)
        return "%d" % (int(self.id))
        
    # Override
    @classmethod
    def get_from_dict( cls, dictionary ):
        return cls.get_from_values(
            dictionary.get('verse_id', 1) )

    # Override
    @classmethod
    def get_from_string( cls, verse_as_string ):
        logger = logging.getLogger(__name__)    

        matches = re.match( ".*(\d+)", verse_as_string )
        if matches:
            line_number = matches.group(1)
            logger.error("verse_as_string: %s.line number: %s"%(verse_as_string,line_number))
            return cls.get_from_values(line_number)
        else:
            return None
    
    @classmethod
    def get_from_values( cls, verse_id ):
        try:
            return cls.objects.filter( id=int(verse_id) ).first()
        except:
            return None
    




class Lection(models.Model):
    verses = models.ManyToManyField(LectionaryVerse)
    description = models.CharField(max_length=100)
        
    def __str__(self):
        return self.description
        

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
    DAY_ABBREVIATIONS = [
        (SUNDAY, 'Sun'),
        (MONDAY, 'Mon'),
        (TUESDAY, 'Tues'),
        (WEDNESDAY, 'Wed'),
        (THURSDAY, 'Th'),
        (FRIDAY, 'Fri'),
        (SATURDAY, 'Sat'),
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
    
    def description( self, abbreviation = False ):
        day_choices = self.DAY_ABBREVIATIONS if abbreviation else DAY_CHOICES
        string = "%s: %s" % (self.get_period_display(), day_choices[self.day_of_week][1] )
        if self.week.isdigit():
            string += ", Week %s" % (self.week )
        elif self.week != "Holy Week":
            string += ", %s" % (self.week )        
    
        if abbreviation:
            string = string.replace("Week", "Wk")
            string = string.replace("Feast of the Cross", "Cross")
            string = string.replace(" Fare", "")
        return string
    def __str__(self):
        return self.description(True)
        
        return string
    class Meta:
        verbose_name_plural = 'Days of year'        

    
class LectionInSystem(models.Model):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE)
    system  = models.ForeignKey('LectionarySystem', on_delete=models.CASCADE)
    day_of_year = models.ForeignKey(DayOfYear, on_delete=models.CASCADE)
    order_on_day = models.IntegerField(default=0)

    def __str__(self):
        return "%s in %s on %s" % ( str(self.lection), str(self.system), str(self.day_of_year) )
        
    def day_description(self):
        if self.order_on_day < 2:
            return str(self.day_of_year)
        return "%s %d" % (str(self.day_of_year), self.order_on_day)
        
    def description(self):
        return "%s. %s" % (self.day_description(), str(self.lection) )
    class Meta:
        ordering = ['day_of_year', 'order_on_day',]
        
        
    

class LectionarySystem(models.Model):
    name = models.CharField(max_length=200)
    lections = models.ManyToManyField(Lection, through=LectionInSystem)
    def __str__(self):
        return self.name    
        
    def lections_in_system(self):
        return LectionInSystem.objects.filter(system=self)        
        
    def lection_for_verse( self, verse ):
        lections_with_verse = verse.lection_set.all()
        lections_in_system = self.lections.all()
        for lection in lections_with_verse:
            if lection in lections_in_system:
                return lection
        return None

    def lection_in_system_for_verse( self, verse ):
        lection = self.lection_for_verse( verse )
        return self.lectioninsystem_set.filter( lection=lection ).first()
        
class Lectionary( Manuscript ):
    system = models.ForeignKey(LectionarySystem, on_delete=models.CASCADE)
    
    @classmethod
    def verse_class(cls):
        return LectionaryVerse
    def verse_search_template(self):
        return "dcodex_lectionary/verse_search.html"
    def location_popup_template(self):
        return 'dcodex_lectionary/location_popup.html'
    class Meta:
        verbose_name_plural = 'Lectionaries'
    
    def render_verse_search( self, request, verse ):
        lection_in_system = self.system.lection_in_system_for_verse( verse )
        return render(request, self.verse_search_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system} )

    def render_location_popup( self, request, verse ):
        lection_in_system = self.system.lection_in_system_for_verse( verse )
        return render(request, self.location_popup_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system} )
