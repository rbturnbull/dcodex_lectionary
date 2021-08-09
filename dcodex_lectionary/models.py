from django.db import models
from django.db.models import F
from django.db.models import Max, Min, Sum
from dcodex.models import Manuscript, Verse, VerseLocation
from dcodex_bible.models import BibleVerse
from polymorphic.models import PolymorphicModel
from dcodex_bible.similarity import * 
from django.shortcuts import render
from lxml import etree

from itertools import chain
import numpy as np
import pandas as pd
import dcodex.distance as distance
from collections import defaultdict
from scipy.special import expit
import gotoh

import logging

DEFAULT_LECTIONARY_VERSE_MASS = 50

class LectionaryVerse(Verse):
    bible_verse = models.ForeignKey(BibleVerse, on_delete=models.CASCADE, default=None, null=True, blank=True )
    unique_string = models.CharField(max_length=100, default="")
    mass = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ('bible_verse',)
    def save(self,*args,**kwargs):
        # Check to see if ID is assigned
        if self.mass == 0:
            self.mass = self.bible_verse.char_count if self.bible_verse else DEFAULT_LECTIONARY_VERSE_MASS
            
        super().save(*args,**kwargs)   
    
    def reference(self, abbreviation = False, end_verse=None):
        if not self.bible_verse:
            if abbreviation and "Heading" in self.unique_string:
                return "Head"
                
            return self.unique_string
        if end_verse:
            return "vv %d–%d" % (self.id, end_verse.id)
        return self.bible_verse.reference( abbreviation )
        
    # Override
    @classmethod
    def get_from_dict( cls, dictionary ):
        return cls.get_from_values(
            dictionary.get('verse_id', 1) )

    # Override
    @classmethod
    def get_from_string( cls, verse_as_string ):
        if verse_as_string.isdigit():
            return cls.get_from_values( verse_as_string )
        return cls.objects.filter( unique_string=verse_as_string ).first()
        
    @classmethod
    def get_from_values( cls, verse_id ):
        try:
            return cls.objects.filter( id=int(verse_id) ).first()
        except:
            return None

    # Override
    def url_ref(self):
        return self.unique_string


    def set_unique_string( self ):
        if not self.bible_verse:
            return

        other_vv = LectionaryVerse.objects.filter( bible_verse=self.bible_verse )
        if self.id:
            other_vv = other_vv.filter( id__lt=self.id )

        self.unique_string = self.bible_verse.reference_abbreviation().replace(" ", '')            
        count = other_vv.count()

        if count > 0:
            self.unique_string += "_%d" % (count+1)
        
        return self.unique_string

    @classmethod
    def new_from_bible_verse( cls, bible_verse ):
        try:
            rank = 1 + cls.objects.aggregate( Max('rank') )['rank__max']
        except:
            rank = 1

        lectionary_verse = cls( bible_verse=bible_verse, rank=rank)
        lectionary_verse.set_unique_string()
        lectionary_verse.save()
        return lectionary_verse

    @classmethod
    def new_from_bible_verse_id( cls, bible_verse_id ):
        bible_verse = BibleVerse.objects.get( id=bible_verse_id )    
        return cls.new_from_bible_verse( bible_verse )
    
    def others_with_bible_verse( self ):
        return LectionaryVerse.objects.filter( bible_verse=self.bible_verse ).exclude( id=self.id )



class Lection(models.Model):
    verses = models.ManyToManyField(LectionaryVerse, through='LectionaryVerseMembership')
    description = models.CharField(max_length=100)
    first_verse_id = models.IntegerField(default=0)
    first_bible_verse_id = models.IntegerField(default=0)
    

    def save(self,*args,**kwargs):
        # Check to see if ID is assigned
        if not self.id:
            return super().save(*args,**kwargs)   
        
        first_verse = self.verses.first()
        if first_verse:
            self.first_verse_id = first_verse.id
            
            self.first_bible_verse_id = first_verse.bible_verse.id if first_verse.bible_verse else 0

        return super().save(*args,**kwargs)   
            
    class Meta:
        ordering = ['first_bible_verse_id','description']
        
    def __str__(self):
        return self.description
    
    def description_max_chars( self, max_chars=40 ):
        description = self.description
        
        if max_chars < 6:
            max_chars = 6
            
        if len(description) < max_chars:
            return description
        return description[:max_chars-3] + "..."        

    def days(self):
        field = 'day'
        ids = {value[field] for value in LectionInSystem.objects.filter(lection=self).values(field) if value[field]}
        return LectionaryDay.objects.get(id__in=ids) # Look for a more efficient way to do this query

    def dates(self):
        """ Deprecated: Use 'days' """
        return self.days()

    def description_with_days( self ):
        description = self.description_max_chars()
        
        days = self.days()
        if len(days) == 0:
            return description
        return "%s (%s)" % (description, ", ".join( [str(day) for day in days] ) )

    def description_with_dates( self ):
        """ Deprecated: Use 'description_with_days' """
        return self.description_with_days()

    def verse_memberships(self):
        return LectionaryVerseMembership.objects.filter( lection=self ).all()

    def reset_verse_order(self):
        for verse_order, verse_membership in enumerate(self.verse_memberships()):
            verse_membership.order = verse_order
            verse_membership.save()
#            print(verse_membership)

    def verse_ids(self):
        return LectionaryVerseMembership.objects.filter(lection=self).values_list( 'verse__id', flat=True )

    def first_verse_id_in_set( self, intersection_set ):
        return LectionaryVerseMembership.objects.filter(lection=self, verse__id__in=intersection_set).values_list( 'verse__id', flat=True ).first()
        # OLD CODE        
        for verse_id in self.verse_ids():        
            if verse_id  in intersection_set:
                return verse_id
        return None

    def last_verse_id_in_set( self, intersection_set ):
        return LectionaryVerseMembership.objects.filter(lection=self, verse__id__in=intersection_set).reverse().values_list( 'verse__id', flat=True ).first()
        # OLD CODE
        for verse_id in LectionaryVerseMembership.objects.filter(lection=self).reverse().values_list( 'verse__id', flat=True ):        
            if verse_id  in intersection_set:
                return verse_id
        return None

    # Deprecated - use add_verses_from_passages_string
    def add_verses_from_range( self, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):
        lection_bible_verse_start = BibleVerse.get_from_string( start_verse_string )
        lection_bible_verse_end   = BibleVerse.get_from_string( end_verse_string )   
        
        # Find verses in other lections to use for this lection
        verses_from_other_lections = []
        for lection_description_with_verses in lection_descriptions_with_verses:
            #print("Finding lection:", lection_description_with_verses)
            lection_with_verses = Lection.objects.get( description=lection_description_with_verses )
            verses_from_other_lections += list( lection_with_verses.verses.all() )

        # Add verses in order, use verses from other lections if present otherwise create them        
        for bible_verse_id in range(lection_bible_verse_start.id, lection_bible_verse_end.id + 1):
            lectionary_verse = None
            for verse_from_other_lections in verses_from_other_lections:
                if verse_from_other_lections.bible_verse.id == bible_verse_id:
                    lectionary_verse = verse_from_other_lections
                    break
            
            if lectionary_verse is None:
                if create_verses == False:
                    print("Trying to create lection %s with range of verses from %s to %s using %s other lections but there are not the right number of verses. i..e %d != %d" %
                        (description, str(lection_bible_verse_start), str(lection_bible_verse_end), lection_descriptions_with_verses, lection.verses.count(), lection_bible_verse_end.id-lection_bible_verse_start.id + 1 ) )
                    sys.exit()
                lectionary_verse = LectionaryVerse.new_from_bible_verse_id( bible_verse_id )
                
            self.verses.add(lectionary_verse)
                    
        self.save()    

    def add_verses_from_passages_string( self, passages_string, overlapping_lection_descriptions=[], overlapping_verses = [], overlapping_lections = [], create_verses=True ):
        bible_verses = BibleVerse.get_verses_from_string( passages_string )
            
        # Find verses in other lections to use for this lection
        overlapping_lections += [Lection.objects.get( description=description ) for description in overlapping_lection_descriptions]
        
        for overlapping_lection in overlapping_lections:
            overlapping_verses += list( overlapping_lection.verses.all() )

        # Add verses in order, use verses from other lections if present otherwise create them        
        for bible_verse in bible_verses: 
            lectionary_verse = None
            for overlapping_verse in overlapping_verses:
                if overlapping_verse.bible_verse and overlapping_verse.bible_verse.id == bible_verse.id:
                    lectionary_verse = overlapping_verse
                    break
            
            if lectionary_verse is None:
                if create_verses == False:
                    raise Exception( "Failed Trying to create lection %s using %s other lections but there are not the right number of verses." % (passages_string,overlapping_verses) )
                lectionary_verse = LectionaryVerse.new_from_bible_verse_id( bible_verse.id )
                
            self.verses.add(lectionary_verse)
        self.save()    

    @classmethod
    def update_or_create_from_description( cls, description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):
        lection, created = cls.objects.get_or_create(description=description)
        if created == False:
            return lection

        lection.verses.clear()  
        lection.add_verses_from_range( start_verse_string, end_verse_string, lection_descriptions_with_verses, create_verses )
    
        return lection 

    @classmethod
    def update_or_create_from_passages_string( cls, passages_string, lection_descriptions_with_verses=[], create_verses=False ):
        lection, created = cls.objects.get_or_create(description=passages_string)
        if created == False:
            return lection

        lection.verses.clear()  
        lection.add_verses_from_passages_string( passages_string, overlapping_lection_descriptions=lection_descriptions_with_verses, create_verses=create_verses )
        return lection    

    @classmethod
    def create_from_passages_string( cls, passages_string, **kwargs ):
        lection = cls(description=passages_string)
        lection.save()        
        lection.add_verses_from_passages_string( passages_string, **kwargs )
        lection.save()        

        return lection    
    def first_verse(self):
        return self.verses.first()
    
    def calculate_mass(self):
        mass = self.verses.aggregate( Sum('mass') ).get('mass__sum')
        return mass
        
    def maintenance(self):
        cumulative_mass_from_lection_start = 0
        for verse_membership in self.verse_memberships():
            verse_membership.cumulative_mass_from_lection_start = cumulative_mass_from_lection_start
            verse_membership.save()
            cumulative_mass_from_lection_start += verse_membership.verse.mass


class LectionaryVerseMembership(models.Model):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE)
    verse  = models.ForeignKey(LectionaryVerse, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    cumulative_mass_from_lection_start = models.IntegerField(default=0, help_text="The total mass of verses from the beginning of the lection until this verse")
    class Meta:
        ordering = ['order','verse__bible_verse']
    def __str__(self):
        return "%d: %s in %s" % (self.order, self.verse, self.lection)
    
class FixedDate(models.Model):
    """
    A liturgical day that corresponds to a fixed date in the calendar.
    
    Because DateTime fields in Django need to be for a particular year, the year chosen was 1003 for September to December and 1004 for January to August. This year was chosen simply because 1004 is a leap year and so includes February 29.
    """
    
    description = models.CharField(max_length=100)
    date = models.DateField(default=None,null=True, blank=True)
    def __str__(self):
        return self.description

    @classmethod
    def get_with_string( cls, date_string ):
        from dateutil import parser
        dt = parser.parse( date_string )
        year = 1003 if dt.month >= 9 else 1004
        dt = dt.replace(year=year)
        #print(dt, date_string)
        return cls.objects.filter( date=dt ).first()
    class Meta:
        ordering = ('date','description')


class LectionaryDay(PolymorphicModel):
    pass


class MiscDay(LectionaryDay):
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description
    
    class Meta:
        ordering = ('description',)


class EothinaDay(LectionaryDay):
    rank = models.IntegerField()

    def __str__(self):
        return f"Eothina {self.rank}"

    class Meta:
        ordering = ('rank',)


class FixedDay(LectionaryDay):
    """
    A lectionary day that corresponds to a fixed date in the calendar.
    
    Because DateTime fields in Django need to be for a particular year, 
    the year chosen was 1003 for September to December and 1004 for January to August. 
    This year was chosen simply because 1004 is a leap year and so includes February 29.
    """
    date = models.DateField(default=None,null=True, blank=True)
    def __str__(self):
        return self.date.strftime('%b %d')

    @classmethod
    def get_with_string( cls, date_string ):
        from dateutil import parser
        dt = parser.parse( date_string )
        year = 1003 if dt.month >= 9 else 1004
        dt = dt.replace(year=year)
        return cls.objects.filter( date=dt ).first()
        
    class Meta:
        ordering = ('date',)


class MovableDay(LectionaryDay):
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
    EPIPHANY = 'T'
    
    SEASON_CHOICES = [
        (EASTER, 'Easter'),
        (PENTECOST, 'Pentecost'),
        (FEAST_OF_THE_CROSS, 'Feast of the Cross'),
        (LENT, 'Lent'),
        (GREAT_WEEK, 'Great Week'),
        (EPIPHANY, 'Epiphany'),
    ]
    season = models.CharField(max_length=1, choices=SEASON_CHOICES)
    
    week = models.CharField(max_length=31)
    weekday_number = models.CharField(max_length=32)    
    earliest_date = models.CharField(max_length=15) 
    latest_date = models.CharField(max_length=15) 
    rank = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        ordering = ('rank','id')

    def description_str( self, abbreviation = False ):
        day_choices = self.DAY_ABBREVIATIONS if abbreviation else DAY_CHOICES
        string = "%s: %s" % (self.get_season_display(), day_choices[self.day_of_week][1] )
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
        return self.description_str(True)
        
    @classmethod   
    def read_season(cls, target):
        target = target.lower().strip()
        for season, season_string in cls.SEASON_CHOICES:
            if season_string.lower().startswith(target):
                return season
        if target.startswith("cross"):
            return cls.FEAST_OF_THE_CROSS
        if target.startswith("theoph"):
            return cls.EPIPHANY
        return None
    
    @classmethod
    def read_day_of_week(cls, target):
        target = target.lower().strip()
        for day, day_abbreviation in cls.DAY_ABBREVIATIONS:
            if target.startswith(day_abbreviation.lower()):
                return day
        return None


class DayOfYear(models.Model):
    "DEPRECATED. See Moveable Day."
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
    EPIPHANY = 'T'
    
    PERIOD_CHOICES = [
        (EASTER, 'Easter'),
        (PENTECOST, 'Pentecost'),
        (FEAST_OF_THE_CROSS, 'Feast of the Cross'),
        (LENT, 'Lent'),
        (GREAT_WEEK, 'Great Week'),
        (EPIPHANY, 'Epiphany'),
    ]
    period = models.CharField(max_length=1, choices=PERIOD_CHOICES)
    
    week = models.CharField(max_length=31)
    weekday_number = models.CharField(max_length=32)    
    earliest_date = models.CharField(max_length=15) 
    latest_date = models.CharField(max_length=15) 
    description = models.CharField(max_length=255)
    
    def description_str( self, abbreviation = False ):
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
        return self.description_str(True)
        
    class Meta:
        verbose_name_plural = 'Days of year'     

    @classmethod   
    def read_period(cls, target):
        target = target.lower().strip()
        for period, period_string in cls.PERIOD_CHOICES:
            if period_string.lower().startswith(target):
                return period
        return None


class LectionInSystem(models.Model):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE, default=None, null=True, blank=True)
    system  = models.ForeignKey('LectionarySystem', on_delete=models.CASCADE)
    day_of_year = models.ForeignKey(DayOfYear, on_delete=models.CASCADE, default=None, null=True, blank=True) # Deprecated 
    fixed_date = models.ForeignKey(FixedDate, on_delete=models.CASCADE, default=None, null=True, blank=True) # Deprecated 
    day = models.ForeignKey(LectionaryDay, on_delete=models.CASCADE, default=None, null=True, blank=True)
    order_on_day = models.IntegerField(default=0) # Deprecated
    cumulative_mass_lections = models.IntegerField(default=-1) # The mass of all the previous lections until the start of this one
    order = models.IntegerField(default=0)
    reference_text_en = models.TextField(default="", blank=True)
    incipit = models.TextField(default="", blank=True)
    reference_membership = models.ForeignKey('LectionInSystem', on_delete=models.CASCADE, default=None, null=True, blank=True)
    occasion_text = models.TextField(default="", blank=True)
    occasion_text_en = models.TextField(default="", blank=True)
    
    
    def __str__(self):
        return "%s in %s on %s" % ( str(self.lection), str(self.system), self.day_description() )
        
    def clone_to_system( self, new_system ):
        return LectionInSystem.objects.get_or_create(
                    system=new_system, 
                    lection=self.lection, 
                    order=self.order,
                    day=self.day,
                    cumulative_mass_lections=self.cumulative_mass_lections,
                    incipit=self.incipit,
                    reference_text_en=self.reference_text_en,
                    reference_membership=self.reference_membership,                    
                )    
        
    def day_description(self):
        if self.order_on_day < 2:
            return str(self.day)
        return "%s (%d)" % (str(self.day), self.order_on_day)
        
    def description(self):
        return "%s. %s" % (self.day_description(), str(self.lection) )
        
    def description_max_chars( self, max_chars=40 ):
        description = self.description()
        
        if max_chars < 6:
            max_chars = 6
            
        if len(description) < max_chars:
            return description
        return description[:max_chars-3] + "..."        
    
    class Meta:
        ordering = ('order', 'day', 'order_on_day',)
        
    def prev(self):
        return self.system.prev_lection_in_system( self )
    def next(self):
        return self.system.next_lection_in_system( self )
    def cumulative_mass_of_verse( self, verse ):
        mass = self.cumulative_mass_lections
        verse_membership = LectionaryVerseMembership.objects.filter( lection=self.lection, verse=verse ).first()
        cumulative_mass_verses = LectionaryVerseMembership.objects.filter( lection=self.lection, order__lt=verse_membership.order ).aggregate( Sum('verse__mass') ).get('verse__mass__sum')
        if cumulative_mass_verses:
            mass += cumulative_mass_verses
        return mass
    
class LectionarySystem(models.Model):
    name = models.CharField(max_length=200)
    lections = models.ManyToManyField(Lection, through=LectionInSystem)

    def __str__(self):
        return self.name   

    def first_lection_in_system(self):
        return self.lections_in_system().first()  

    def last_lection_in_system(self):
        return self.lections_in_system().last()  

    def first_lection(self):
        first_lection_in_system = self.first_lection_in_system()
        return first_lection_in_system.lection

    def first_verse(self):
        first_lection = self.first_lection()
        return first_lection.first_verse()

    def maintenance(self):
        self.reset_order()
        self.calculate_masses()
        
    def find_movable_day( self, **kwargs ):
        day = MovableDay.objects.filter(**kwargs).first()
        print('Day:', day)
        if day:
            return LectionInSystem.objects.filter(system=self, day=day).first()
        return None

    def find_fixed_day( self, last=False, **kwargs ):
        memberships = self.find_fixed_day_all(**kwargs)
        if not memberships:
            return None
        if last:
            return memberships.last()
        return memberships.first()

    def find_fixed_day_all( self, **kwargs ):
        date = FixedDay.objects.filter(**kwargs).first()
        if date:
            return LectionInSystem.objects.filter(system=self, day=date).all()
        return None
        
    def reset_order(self):
        lection_memberships = self.lections_in_system()
        for order, lection_membership in enumerate(lection_memberships.all()):
            lection_membership.order = order
            lection_membership.save()
            lection_membership.lection.reset_verse_order()
        
    def lections_in_system(self):
        return LectionInSystem.objects.filter(system=self)   

    def lections_in_system_min_verses(self, min_verses=2):
        return [m for m in self.lections_in_system().all() if m.lection.verses.count() >= min_verses]

    def export_csv(self, filename) -> pd.DataFrame:
        """
        Exports the lectionary system as a CSV.

        Returns the lectionary system as a dataframe.
        """
        df = self.dataframe()
        df.to_csv(filename)
        return df
    
    def dataframe(self) -> pd.DataFrame:
        """
        Returns the lectionary system as a pandas dataframe.
        """
        data = []
        columns = ["lection", 'season', 'week', 'day']
        for lection_membership in self.lections_in_system():
            if type(lection_membership.day) != MovableDay:
                raise NotImplementedError(f"Cannot yet export for days of type {type(lection_membership.day)}.")
            data.append(
                [
                    lection_membership.lection.description, 
                    lection_membership.day.get_season_display(), 
                    lection_membership.day.week, 
                    lection_membership.day.get_day_of_week_display(), 
                ]
            )
        df = pd.DataFrame(data, columns=columns)
        return df

    def import_csv(self, csv, replace=False, create_verses=True):
        """ 
        Reads a CSV and lections from it into this lectionary system.

        The CSV file must have columns corresponding to 'lection', 'season', 'week', 'day', 'parallels' (optional).
        """
        df = pd.read_csv(csv)
        required_columns = ['season', 'week', 'day', 'lection']
        for required_column in required_columns:
            if not required_column in df.columns:
                raise ValueError(f"No column named '{required_column}' in {df.columns}.")

        for _, row in df.iterrows():
            season = MovableDay.read_season(row['season'])
            week = row['week']
            day_of_week = MovableDay.read_day_of_week(row['day'])
            day_of_year = MovableDay.objects.filter( season=season, week=week, day_of_week=day_of_week ).first()
            if not day_of_year:
                raise ValueError(f"Cannot find day for row\n{row}")
            
            if "parallels" in row and not pd.isna(row["parallels"]):
                parallels = row["parallels"].split("|")
            else:
                parallels = []

            lection = Lection.update_or_create_from_passages_string( 
                row["lection"], 
                lection_descriptions_with_verses=parallels, 
                create_verses=create_verses,
            )

            if replace:
                self.replace_with_lection(day_of_year, lection)
            else:
                self.add_lection( day_of_year, lection )
        
    def next_lection_in_system(self, lection_in_system):
        found = False
        for object in self.lections_in_system().all():
            if object == lection_in_system:
                found = True
            elif found:
                return object
            
    def prev_lection_in_system(self, lection_in_system):
        found = False
        for object in self.lections_in_system().all().reverse():
            if object == lection_in_system:
                found = True
            elif found:
                return object
            
    def calculate_masses( self ):
        cumulative_mass = 0.0
        for lection_in_system in self.lections_in_system().all():
            lection_in_system.cumulative_mass_lections = cumulative_mass
            lection_in_system.save()

            try:
                cumulative_mass += lection_in_system.lection.calculate_mass()
            except:
                print( 'Failed to calculate mass:', lection_in_system.lection )
                continue

    @classmethod
    def calculate_masses_all_systems( cls ):
        for system in cls.objects.all():
            system.calculate_masses()
    @classmethod
    def maintenance_all_systems( cls ):
        print("Doing maintenance for each lection")
        for lection in Lection.objects.all():
            print(lection)
            lection.maintenance()
        print("Doing maintenance for each system")            
        for system in cls.objects.all():
            print(system)        
            system.maintenance()
    
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
        
    def get_max_order( self ):
        return self.lections_in_system().aggregate(Max('order')).get('order__max')
    
    def add_lection( self, day, lection ):
        membership, created = LectionInSystem.objects.get_or_create(system=self, lection=lection, day=day)    
        if created == True:
            max_order = self.get_max_order()
            membership.order = max_order + 1
        membership.save()
        return membership
      
    def add_lection_from_description( self, day, lection_description ):
        lection, created = Lection.objects.get_or_create(description=lection_description)
        return self.add_lection( day, lection )
                
    def add_new_lection_from_description( self, day, lection_description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):        
        lection = Lection.update_or_create_from_description(description=lection_description, start_verse_string=start_verse_string, end_verse_string=end_verse_string, lection_descriptions_with_verses=lection_descriptions_with_verses, create_verses=create_verses)    
        return self.add_lection( day, lection )
       
    def add_new_lection_from_passages_string( self, day, passages_string, **kwargs ):        
        lection = Lection.update_or_create_from_passages_string(passages_string=passages_string, **kwargs)    
        return self.add_lection( day, lection )
       
    def delete_all_on_day( self, day ):
        print("Deleting all on Day of year:", day )
        lection_memberships = LectionInSystem.objects.filter(system=self, day=day).delete()
            
    def replace_with_lection( self, day, lection ):
        self.delete_all_on_day( day )
        print("Adding:", lection)
        return self.add_lection( day, lection )
        
    def insert_lection( self, day, lection, insert_after=None ):
        order = None
        if insert_after is not None:
            insert_after_membership = LectionInSystem.objects.filter(system=self, lection=insert_after).first()
            if insert_after_membership:
                order = insert_after_membership.order + 1
                LectionInSystem.objects.filter(system=self, order__gte=order).update( order=F('order') + 1 )
                
        
        if not order:
            print('order is none')
            print('insert_after', insert_after)
            print('insert_after_membership  ', insert_after_membership )
            print('system  ', self )
            return None

        membership = self.add_lection( day, lection )        
        membership.order = order
        membership.save()
        return membership
        
    def replace_with_new_lection_from_description( self, day, lection_description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):        
        lection = Lection.update_or_create_from_description(description=lection_description, start_verse_string=start_verse_string, end_verse_string=end_verse_string, lection_descriptions_with_verses=lection_descriptions_with_verses, create_verses=create_verses)    
        self.replace_with_lection( day, lection )
        return lection

    def empty( self ):
        """ This method removes references to all lections in this system and leaves the lectionary system empty. """
        LectionInSystem.objects.filter( system=self ).delete()
        
    def clone_to_system( self, new_system ):
        new_system.empty()
        for lection_membership in self.lections_in_system().all():
            lection_membership.clone_to_system( new_system )
    
    def clone_to_system_synaxarion( self, new_system ):
        new_system.empty()
        for lection_membership in LectionInSystem.objects.filter( system=self, day__in=MovableDay.objects.all() ).all():  # There should be a more efficient way to do this query
            lection_membership.clone_to_system( new_system )
    
    def clone_to_system_with_name(self, new_system_name ):
        new_system, created = LectionarySystem.objects.get_or_create(name=new_system_name)
        self.clone_to_system( new_system )
        return new_system

    def cumulative_mass( self, verse ):
        lection_in_system = self.lection_in_system_for_verse( verse )
        if lection_in_system:
            return lection_in_system.cumulative_mass_of_verse( verse )
        return 0
        
    def verse_from_mass_difference( self, reference_verse, additional_mass ):
        logger = logging.getLogger(__name__)            

        logger.error("ref_verse "+str(reference_verse))
        logger.error("additional_mass "+str(additional_mass))
        cumulative_mass = self.cumulative_mass(reference_verse) + additional_mass
        logger.error("cumulative_mass "+str(cumulative_mass))
        
        
        
        lection_membership = LectionInSystem.objects.filter( system=self, cumulative_mass_lections__lte=cumulative_mass ).order_by( '-cumulative_mass_lections' ).first()
        logger.error("lection_membership "+str(lection_membership))
        logger.error("lection_membership.cumulative_mass_lections "+str(lection_membership.cumulative_mass_lections))
        
        if lection_membership == None:
            return None
            
        mass_from_start_of_lection = cumulative_mass - lection_membership.cumulative_mass_lections
        logger.error("mass_from_start_of_lection "+str(mass_from_start_of_lection))

        
        verse_membership = LectionaryVerseMembership.objects.filter( lection=lection_membership.lection, cumulative_mass_from_lection_start__lte=mass_from_start_of_lection ).order_by( '-cumulative_mass_from_lection_start' ).first()

        if verse_membership:
            return verse_membership.verse
            
        return None                
    
    def create_reference( self, date, insert_after, description="", reference_text_en="", reference_membership=None, has_incipit=False ):
        if not description:
            description = "Reference: "+str(date)
            heading_description = str(date) + " Heading"
            incipit_description = str(date) + " Incipit"
        else:
            heading_description = description + " Heading"
            incipit_description = description + " Incipit"

        # Create Lection
        print('getting', description)
        lection, created = Lection.objects.get_or_create(description=description)
        print('created', description)        
        if created:
            # Add heading
            heading_verse, created = LectionaryVerse.objects.get_or_create( bible_verse=None, unique_string=heading_description, rank=0 )        
            lection.verses.add( heading_verse )
        
            # Add Incipit
            if has_incipit:
                incipit, created = LectionaryVerse.objects.get_or_create( bible_verse=None, unique_string=incipit_description, rank=0 )
                lection.verses.add( incipit )
            lection.save()
            
        
        # Insert Into System
        membership = self.insert_lection( date, lection, insert_after )
        print('membership', membership)
        membership.reference_membership = reference_membership
        membership.reference_text_en = reference_text_en
        membership.save()
        
        return membership
        

        
class Lectionary( Manuscript ):
    system = models.ForeignKey(LectionarySystem, on_delete=models.CASCADE)
    
    @classmethod
    def verse_class(cls):
        return LectionaryVerse
        
    @classmethod
    def verse_from_id(cls, verse_id):
        verse = super().verse_from_id(verse_id)
        if verse:
            return verse

        return cls.verse_class().objects.filter(bible_verse_id=verse_id).first()        
    # Override
    def verse_search_template(self):
        return "dcodex_lectionary/verse_search.html"

    # Override        
    def location_popup_template(self):
        return 'dcodex_lectionary/location_popup.html'
    class Meta:
        verbose_name_plural = 'Lectionaries'
    
    # Override    
    def render_verse_search( self, request, verse ):
        lection_in_system = self.system.lection_in_system_for_verse( verse )
        if lection_in_system is None:
            lection_in_system = self.system.first_lection_in_system()
            verse = lection_in_system.lection.first_verse()
        return render(request, self.verse_search_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system, 'next_verse':self.next_verse(verse), 'prev_verse':self.prev_verse(verse),} )

    # Override
    def render_location_popup( self, request, verse ):
        lection_in_system = self.system.lection_in_system_for_verse( verse )
        return render(request, self.location_popup_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system, 'next_verse':self.next_verse(verse), 'prev_verse':self.prev_verse(verse),} )

    # Override
    def comparison_texts( self, verse, manuscripts = None ):
        lectionary_comparisons = super().comparison_texts( verse, manuscripts )
        
        # Find all other lectionary verse transcriptions with this Bible Verse
        lectionary_verses_with_bible_verse = verse.others_with_bible_verse()
        
        lectionary_comparisons_same_bible_verse = self.transcription_class().objects.filter( verse__in=lectionary_verses_with_bible_verse )
        if manuscripts:
            lectionary_comparisons_same_bible_verse = lectionary_comparisons_same_bible_verse.filter( manuscript__in=manuscripts )

        continuous_text_comparisons = super().comparison_texts( verse.bible_verse, manuscripts )
        
#        return list(chain(lectionary_comparisons, continuous_text_comparisons))
        return list(chain(lectionary_comparisons, lectionary_comparisons_same_bible_verse.all(), continuous_text_comparisons))        

    # Override
    def accordance(self):
        """ Returns a string formatted as an Accordance User Bible """
        user_bible = ""
        
        # Loop over all transcriptions and put them in a dictionary based on the bible verse
        bible_verse_to_transcriptions_dict = defaultdict(list)
        for transcription in self.transcriptions():
            transcription_clean = transcription.remove_markup()
            if transcription.verse.bible_verse:
                bible_verse_to_transcriptions_dict[transcription.verse.bible_verse].append(transcription_clean)

        # Loop over the distinct Bible verses in order
        bible_verses = sorted(bible_verse_to_transcriptions_dict.keys(), key=lambda bible_verse: bible_verse.id) 
        for bible_verse in bible_verses:
            transcriptions_txt = " | ".join(bible_verse_to_transcriptions_dict[bible_verse])
            user_bible += f"{bible_verse} <color=black></color>{transcriptions_txt}<br>\n"

        return user_bible

    def tei_element_text( self, ignore_headings=True ):
        text = etree.Element("text")
        body  = etree.SubElement(text, "body")
        for membership in self.system.lectioninsystem_set.all():
            lection_div  = etree.SubElement(body, "div", type="lection", n=membership.description() )
            for verse_index, verse in enumerate(membership.lection.verses.all()):
                if not verse.bible_verse:
                    continue
                
                transcription = self.transcription( verse )
                if transcription:
                    verse_tei_id = transcription.verse.bible_verse.tei_id()
                    tei_text = transcription.tei()
                    # ab = etree.SubElement(body, "ab", n=verse_tei_id)
                    ab = etree.fromstring( f'<ab n="{verse_tei_id}">{tei_text}</ab>' )
                    lection_div.append(ab)

        return text

    def next_verse( self, verse, lection_in_system = None ):
        if lection_in_system == None:
            lection_in_system = self.system.lection_in_system_for_verse( verse )

        if lection_in_system == None:
            return None        
        next_verse = lection_in_system.lection.verses.filter( rank__gt=verse.rank ).order_by('rank').first()
        if not next_verse:
            lection_in_system = lection_in_system.next()
            if lection_in_system and lection_in_system.lection:
                next_verse = lection_in_system.lection.verses.order_by('rank').first()
        return next_verse     

    def prev_verse( self, verse, lection_in_system = None ):
        if lection_in_system == None:
            lection_in_system = self.system.lection_in_system_for_verse( verse )
        if lection_in_system == None:
            return None        
        
        prev_verse = lection_in_system.lection.verses.filter( rank__lt=verse.rank ).order_by('-rank').first()
        if not prev_verse:
            lection_in_system = lection_in_system.prev()
            if not lection_in_system:
                return None
            
            prev_verse = lection_in_system.lection.verses.order_by('-rank').first()
        return prev_verse

    def verse_membership( self, verse ):
        return LectionaryVerseMembership.objects.filter( verse=verse, lection__lectioninsystem__system=self.system ).first()
            
    def location_before_or_equal( self, verse ):
        if not verse:
            return None
        logger = logging.getLogger(__name__)            
    
        current_verse_membership = self.verse_membership( verse )
        if not current_verse_membership:
            return None
        
        verse_ids_with_locations = set(self.verse_ids_with_locations())
        
        # Search within current lection
        verse_id = LectionaryVerseMembership.objects.filter(
                        lection=current_verse_membership.lection, 
                        order__lte=current_verse_membership.order,
                        verse__id__in=verse_ids_with_locations
                    ).values_list( 'verse__id', flat=True ).last()
        
        # Search in previous lections if necessary
        if not verse_id:                                                    
            current_lection_in_system = self.system.lection_in_system_for_verse( verse )

            verse_id = LectionInSystem.objects.filter( 
                            system=self.system, 
                            order__lt=current_lection_in_system.order, 
                            lection__verses__id__in=verse_ids_with_locations,
                        ).values_list('lection__verses', flat=True).last()  
        if verse_id:
            return VerseLocation.objects.filter( manuscript=self, verse__id=verse_id ).first()        
                         
        return None                

    def location_after( self, verse ):
        if not verse:
            return None
#        logger = logging.getLogger(__name__)            
    
        current_verse_membership = self.verse_membership( verse )
        if not current_verse_membership:
            return None
        
        verse_ids_with_locations = self.verse_ids_with_locations()
        
        # Search within current lection
        verse_id = LectionaryVerseMembership.objects.filter(
                        lection=current_verse_membership.lection, 
                        order__gt=current_verse_membership.order,
                        verse__id__in=verse_ids_with_locations
                    ).values_list( 'verse__id', flat=True ).first()

        # Search in subsequent lections if necessary
        if not verse_id:                                                    
            current_lection_in_system = self.system.lection_in_system_for_verse( verse )


            verse_id = LectionInSystem.objects.filter( 
                            system=self.system, 
                            order__gt=current_lection_in_system.order, 
                            lection__verses__id__in=verse_ids_with_locations,
                        ).values_list('lection__verses', flat=True).first()  
        if verse_id:
            return VerseLocation.objects.filter( manuscript=self, verse__id=verse_id ).first()
                                       
        return None                
                
                
                
                
    def last_location( self, pdf ):
        return VerseLocation.objects.filter( manuscript=self, pdf=pdf ).order_by('-page', '-y').first()
    def first_location( self, pdf ):
        return VerseLocation.objects.filter( manuscript=self, pdf=pdf ).order_by('page', 'y').first()
        
    def first_verse( self ):
        return self.system.first_verse()
    def first_empty_verse( self ):
        verse = self.first_verse()
        while verse is not None:
            if self.transcription( verse ) is None:
                return verse
            else:
                verse = self.next_verse( verse )
        return None
        
        
    # Override
    def title_dict( self, verse ):
        day_description = ""    
        lection_in_system = self.system.lection_in_system_for_verse( verse )    
        if lection_in_system:
             day_description = lection_in_system.day_description()
        url_ref = verse.url_ref()


        dict = { 
            'title': "%s %s %s" % (self.siglum, day_description, verse.reference_abbreviation() ), 
            'url': "/dcodex/ms/%s/%s/" % ( self.siglum, url_ref ),
            'verse_url_ref': url_ref, 
        }
        return dict    

    def lection_transcribed_count( self, lection ):
        return self.transcription_class().objects.filter( manuscript=self, verse__in=lection.verses.all() ).count()

    def transcribed_count_df( self ):
        total_transcribed_count = 0
        total_verses_count = 0
        
        df = pd.DataFrame(columns=('Lection', 'Day', 'Verses Transcribed', 'Verses Count'))
        i=0
        for i, lection_in_system in enumerate(self.system.lections_in_system()):
            lection = lection_in_system.lection
            verses_count = lection.verses.count()
            transcribed_verses_count = self.lection_transcribed_count( lection )
            
            total_transcribed_count += transcribed_verses_count
            total_verses_count += verses_count

            df.loc[i] = [str(lection), lection_in_system.day_description(), transcribed_verses_count, verses_count]
        df.loc[i+1] = ["Total", "", total_transcribed_count, total_verses_count]
            
        df['Percentage'] = df['Verses Transcribed']/df['Verses Count']*100.0
        return df       

    def transcriptions_in_lections( self, lections, ignore_incipits=False ):
        transcriptions = []
        for lection in lections:
            print(lection)
            for verse_index, verse in enumerate(lection.verses.all()):
                if verse_index == 0 and ignore_incipits:
                    continue
                
                transcription = self.transcription( verse )
                if transcription:
                    transcriptions.append( transcription )

        return transcriptions
            
    def transcriptions_in_lections_dict( self, **kwargs ):
        return { transcription.verse.bible_verse.id : transcription.transcription for transcription in self.transcriptions_in_lections( **kwargs ) }
    
    def transcription( self, verse ):
        if type(verse) == LectionaryVerse:
            return super().transcription(verse)
        if type(verse) == BibleVerse:
            lectionary_verse = self.verse_class().objects.filter(bible_verse=verse).first()        # HACK This will give the first version, not necessarily the one we want!
            return super().transcription(lectionary_verse)

        return None

    def similarity_lection( self, lection, comparison_mss, similarity_func=distance.similarity_levenshtein, ignore_incipits=False ):

        similarity_values = np.zeros( (len(comparison_mss),) )
        counts = np.zeros( (len(comparison_mss),), dtype=int )
        has_seen_incipit = False
        for verse_index, verse in enumerate(lection.verses.all()):
            if not verse.bible_verse:
                continue
            if not has_seen_incipit:
                has_seen_incipit = True
                if ignore_incipits:
                    continue
            my_transcription = self.normalized_transcription( verse )
            if not my_transcription:
                continue
            
            for ms_index, ms in enumerate(comparison_mss):
                comparison_transcription = ms.normalized_transcription( verse ) if type(ms) is Lectionary else ms.normalized_transcription( verse.bible_verse )
                if not comparison_transcription:
                    continue
                
                similarity_values[ms_index] += similarity_func( my_transcription, comparison_transcription )
                counts[ms_index] += 1

        averages = []
        for similarity_value, count in zip(similarity_values, counts):
            average = None if count == 0 else similarity_value/count
            averages.append(average)
        return averages

    def similarity_probabilities_lection( self, lection, comparison_mss, weights, gotoh_param, prior_log_odds=0.0, ignore_incipits=False ):
        gotoh_totals = np.zeros( (len(comparison_mss),4), dtype=np.int32 )   
        weights = np.asarray(weights)  
        
        for verse_index, verse in enumerate(lection.verses.all()):
            if verse_index == 0 and ignore_incipits:
                continue
            my_transcription = self.normalized_transcription( verse )
            if not my_transcription:
                continue
            
            for ms_index, ms in enumerate(comparison_mss):
                comparison_transcription = ms.normalized_transcription( verse ) if type(ms) is Lectionary else ms.normalized_transcription( verse.bible_verse )
                if not comparison_transcription:
                    continue

                counts = gotoh.counts( my_transcription, comparison_transcription, *gotoh_param )
                gotoh_totals[ms_index][:] += counts

        results = []        
        for ms_index in range(len(comparison_mss)):
            length = gotoh_totals[ms_index].sum()            
            similarity = 100.0 * gotoh_totals[ms_index][0]/length if length > 0 else np.NAN
            logodds = prior_log_odds + np.dot( gotoh_totals[ms_index], weights )
            posterior_probability = expit( logodds )
            
            results.extend([similarity, posterior_probability])
                        
        return results

    def similarity_df( self, comparison_mss, min_verses = 2, **kwargs ):
        columns = ['Lection']
                
        columns += [ms.siglum for ms in comparison_mss]
        
        df = pd.DataFrame(columns=columns)
        for i, lection_in_system in enumerate(self.system.lections_in_system().all()):
            lection = lection_in_system.lection
            if lection.verses.count() < min_verses:
                continue
                
            averages = self.similarity_lection( lection, comparison_mss, **kwargs )
                
            df.loc[i] = [str(lection_in_system)] + averages

        return df    
        
                        
    def similarity_probabilities_df( self, comparison_mss, min_verses=2, **kwargs ):
        columns = ['Lection','Lection_Membership__id','Lection_Membership__order']
        for ms in comparison_mss:
            columns.extend( [ms.siglum + "_similarity", ms.siglum + "_probability"] )
                
        
        df = pd.DataFrame(columns=columns)
        index = 0
        for lection_in_system in self.system.lections_in_system().all():
            lection = lection_in_system.lection
            if lection.verses.count() < min_verses:
                continue

#            if ignore_untranscribed and self.lection_transcribed_count( lection ) == 0:
#                print("Ignoring untranscribed lection:", lection)
#                continue
            
            results = self.similarity_probabilities_lection( lection, comparison_mss, **kwargs )
                
            df.loc[index] = [str(lection_in_system), lection_in_system.id, lection_in_system.order] + results
            index += 1

        print('similarity_probabilities_df indexes:', index)
        return df  
          
    def similarity_families_array( self, comparison_mss, start_verse, end_verse, threshold, **kwargs ):
        verse_count = end_verse.rank - start_verse.rank + 1
        families_array = np.zeros( (verse_count,) )
        
        
        UNCERTAIN = 1
        MIXED = 2
        
        
        for i, lection in enumerate(self.system.lections.all()):
            averages = self.similarity_lection( lection, comparison_mss, **kwargs )
 #           print(lection, averages)
            
            max_index = None
            max_average = 0.0
            for ms_index, average in enumerate( averages ):
                print(average)
                print( 'average is not None', average is not None )
#                print( 'average > max_average', average > max_average )
                if average is not None and average > max_average:
                    max_index = ms_index
                    max_average = average
            
            if max_index is None:
                continue
            family = max_index + MIXED + 1 if max_average > threshold else UNCERTAIN
            print( lection, max_index, family, max_average, averages )
            
            for lectionary_verse in lection.verses.all():
                array_index = lectionary_verse.bible_verse.rank - start_verse.rank
                if families_array[array_index] <= UNCERTAIN:
                    families_array[array_index] = family
                elif families_array[array_index] != family:
                    families_array[array_index] = MIXED
                
        return families_array   
        
    def lections_agreeing_with( self, comparison_mss, threshold, **kwargs ):
        lections_agreeing_with = defaultdict( list )
        for i, lection in enumerate(self.system.lections.all()):
            averages = self.similarity_lection( lection, comparison_mss, **kwargs )
            
            max_index = None            
            max_average = 0.0
            for ms_index, average in enumerate( averages ):
                if average is not None and average > max_average:
                    max_index = ms_index
                    max_average = average
            if max_index is None:
                continue
            if max_average > threshold:
                lections_agreeing_with[max_index].append( lection )
        
        # Add Sigla to dictionary
        for ms_index, ms in enumerate( comparison_mss ):
            lections_agreeing_with[ ms.siglum ] = lections_agreeing_with[ ms_index ]
            
        return lections_agreeing_with
            
            
        
    def verse_from_mass_difference( self, reference_verse, additional_mass ):
        return self.system.verse_from_mass_difference( reference_verse, additional_mass )


    def cumulative_mass( self, verse ):
        return self.system.cumulative_mass(verse)
        
    def distance_between_verses( self, verse1, verse2 ):
        return self.cumulative_mass( verse2 ) - self.cumulative_mass( verse1 )
        
        
    def plot_lections_similarity( 
                self, 
                mss_sigla, 
                lections = None,
                min_lection_index = None,            
                max_lection_index = None,            
                output_filename = None,
                csv_filename = None, 
                force_compute = False, 
                gotoh_param = [6.6995597099885345, -0.9209875054657459, -5.097397327423096, -1.3005714416503906], # From PairHMM of whole dataset
                weights = [0.07124444438506426, -0.2723489152810223, -0.634987796501936, -0.05103656566400282], # From whole dataset
                figsize=(12,7),
                colors = ['#007AFF', '#6EC038', 'darkred', 'magenta'],
                mode = LIKELY__UNLIKELY,
                xticks = [],
                xticks_rotation=0,
                minor_markers=1,
                ymin=60,
                ymax=100,
                prior_log_odds=0.0,
                annotations=[],            
                annotation_color='red',
                annotations_spaces_to_lines=False,              
                legend_location="best",
                circle_marker=True,
                highlight_regions=[],
                highlight_color='yellow',
                fill_empty=True,
                space_evenly=False,
                ignore_untranscribed=False,
                    ):

        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        from matplotlib import rcParams
        rcParams['font.family'] = 'Linux Libertine O'
        rcParams.update({'font.size': 14})
    
        #plt.rc('text', usetex=True)
        #plt.rc('text.latex', preamble=r'\usepackage{amsmath}')

        import matplotlib.ticker as mtick
        import matplotlib.lines as mlines
        from os import access, R_OK
        from os.path import isfile

        from matplotlib.ticker import FixedLocator

        fig, ax = plt.subplots(figsize=figsize)

        mss = [Manuscript.find( siglum ) for siglum in mss_sigla.keys()]
    
        if not force_compute and csv_filename and isfile( csv_filename ) and access(csv_filename, R_OK):
            df = pd.read_csv(csv_filename)
        else:    
            df = self.similarity_probabilities_df( mss, weights=weights, gotoh_param=gotoh_param, prior_log_odds=prior_log_odds )
            if csv_filename:
                df.to_csv( csv_filename )

        if min_lection_index:
            if isinstance( min_lection_index, LectionInSystem ):
                min_lection_index = min_lection_index.order
            df = df[ df['Lection_Membership__order'] >= min_lection_index ]
        if max_lection_index:
            if isinstance( max_lection_index, LectionInSystem ):
                max_lection_index = max_lection_index.order
            print('max_lection_index', max_lection_index)
            df = df[df['Lection_Membership__order'] <= max_lection_index ]
            
        if lections:
            lection_ids = []
            for lection in lections:
                if isinstance(lection,LectionInSystem):
                    lection_ids.append( lection.id )
                else:
                    lection_ids.append( lection )
#            print(df)
            df = df[ df['Lection_Membership__id'].isin( lection_ids ) ]
#            print(df)
#            print(lection_ids)
#            return
    
        min = df.index.min()
        max = df.index.max()
        if fill_empty:
            df = df.set_index( 'Lection_Membership__order' )    
            df = df.reindex( np.arange( min, max+1 ) )  
        
        if space_evenly:
            df.index = np.arange( len(df.index) )
    
        print(df)
        #return

        circle_marker = 'o' if circle_marker else ''
    
        for index, ms_siglum in enumerate(mss_sigla.keys()): 
            ms_df = df[ df[ms_siglum+'_similarity'].notnull() ] if ignore_untranscribed else df
            
           
            if mode is HIGHLY_LIKELY__LIKELY__ELSE:
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.95), '-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Highly Likely)" );
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask( (ms_df[ms_siglum+"_probability"] > 0.95) | (ms_df[ms_siglum+"_probability"] < 0.5)), '-', color=colors[index], linewidth=1.5, label=mss_sigla[ms_siglum] + " (Likely)" );        
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] > 0.95), '--', color=colors[index], linewidth=0.5, label=mss_sigla[ms_siglum] + " (Unlikely)" );        
        
            elif mode is HIGHLY_LIKELY__ELSE:
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.95), '-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Highly Likely)" );
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'], '--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] );        
            else:    
            
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.5), marker=circle_marker, linestyle='-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Likely)", zorder=11, markersize=8.0,  markerfacecolor=colors[index], markeredgecolor=colors[index]);
                plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'], marker=circle_marker, linestyle='--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] + " (Unlikely)", zorder=10, markerfacecolor='white', markeredgecolor=colors[index], markersize=5.0 );        
    #            plt.plot(df.index, df[ms_siglum+'_similarity'].mask(df[ms_siglum+"_probability"] > 0.5), '--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] + " (Unlikely)" );        

        plt.ylim([ymin, ymax])
        ax.set_xticklabels([])
    
        plt.ylabel('Similarity', horizontalalignment='right', y=1.0)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    
    
        #######################
        ##### Grid lines  #####
        ####################### 
    
    #    first_lection_membership = self.system.first_lection_in_system()
    #    last_lection_membership = self.system.last_lection_in_system()
           
        ###### Major Grid Lines ######
        major_tick_locations = []    
        major_tick_annotations = []

        for membership in xticks:
            if type(membership) == tuple:
                if not isinstance( membership[0], LectionInSystem ):
                    print("Trouble with membership:", membership)
                    continue
                print( 'looking for:', membership[0].id, membership )                    
                x = df.index[ df['Lection_Membership__id'] == membership[0].id ].values.item()
                description = membership[-1]
            else:
                if not isinstance( membership, LectionInSystem ):
                    print("Trouble with membership:", membership)
                    continue
            
                print( 'looking for:', membership.id, membership )
                x = df.index[ df['Lection_Membership__id'] == membership.id ].values.item()
                description = str(membership.day)

            if annotations_spaces_to_lines:
                description = description.replace( ' ', "\n" )
            major_tick_locations.append( x )
            major_tick_annotations.append( description )
            
        plt.xticks(major_tick_locations, major_tick_annotations, rotation=xticks_rotation )        
        linewidth = 2
        ax.xaxis.grid(True, which='major', color='#666666', linestyle='-', alpha=0.4, linewidth=linewidth)
            
        ###### Minor Grid Lines ######
        minor_ticks = [x for x in df.index if x not in major_tick_locations and x % minor_markers == 0]
        ax.xaxis.set_minor_locator(FixedLocator(minor_ticks))
        ax.xaxis.grid(True, which='minor', color='#666666', linestyle='-', alpha=0.2, linewidth=1,)

        ###### Annotations ######
        for annotation in annotations:
            if type(annotation) == tuple:
                if not isinstance( annotation[0], LectionInSystem ):
                    print("Trouble with annotation:", annotation)
                    continue
            
                annotation_x = df.index[ df['Lection_Membership__id'] == annotation[0].id ].item()
                annotation_description = annotation[-1]
            else:
                if not isinstance( annotation, LectionInSystem ):
                    print("Trouble with annotation:", annotation)
                    continue
            
                annotation_x = df.index[ df['Lection_Membership__id'] == annotation.id ].item()
                annotation_description = str(annotation.day)            

            if annotations_spaces_to_lines:
                annotation_description = annotation_description.replace( ' ', "\n" )
            plt.axvline(x=annotation_x, color=annotation_color, linestyle="--")
            ax.annotate(annotation_description, xy=(annotation_x, ymax), xycoords='data', ha='center', va='bottom',xytext=(0,10), textcoords='offset points', fontsize=10, family='Linux Libertine O', color=annotation_color)

        ax.legend(shadow=False, title='', framealpha=1, edgecolor='black', loc=legend_location, facecolor="white", ncol=2).set_zorder(100)
        
        for region in highlight_regions:
            from matplotlib.patches import Rectangle
            region_start = region[0]
            if isinstance(region_start, LectionInSystem):
                region_start = df.index[ df['Lection_Membership__id'] == region_start.id ].item()                
            region_end = region[1]
            if isinstance(region_end, LectionInSystem):
                region_end = df.index[ df['Lection_Membership__id'] == region_end.id ].item()                
            
            rect = Rectangle((region_start,ymin),region_end-region_start,ymax-ymin,linewidth=1,facecolor=highlight_color)
            ax.add_patch(rect)


        plt.show()
    
        if output_filename:
            fig.tight_layout()
            fig.savefig(output_filename)    
            
        notnull = False
        for index, ms_siglum in enumerate(mss_sigla.keys()):     
            notnull = notnull | df[ms_siglum+'_similarity'].notnull()
            
        ms_df = df[ notnull ]
        print(ms_df)
                
        for index, ms_siglum in enumerate(mss_sigla.keys()):     
            print( ms_siglum, df[ms_siglum+'_similarity'].mean() )

        print("Number of lections:", ms_df.shape[0])


class AffiliationLectionsSet(AffiliationBase):
    """ An abstract Affiliation class which is active only in certain lections which is defined by a function. """    
    class Meta:
        abstract = True
    
    def lections_where_active( self ):
        """ This needs to be set by child class """
        raise NotImplementedError
    
    def is_active( self, verse ):
        """ This affiliation is active whenever the verse is in the lection. If the verse is of type BibleVerse, then it is active if the lections have a mapping to that verse. """
        if isinstance( verse, LectionaryVerse ):
            return self.lections_where_active().filter( verses__id=verse.id ).exists()
        elif isinstance( verse, BibleVerse ):
            return self.lections_where_active().filter( verses__bible_verse__id=verse.id ).exists()
        return False

    def manuscript_and_verse_ids_at( self, verse ):
        if isinstance( verse, LectionaryVerse ):
            return super().manuscript_and_verse_ids_at( verse )
        
        manuscript_ids = self.manuscript_ids_at(verse)
        pairs = set()

        if len(manuscript_ids) > 0:
            verses = LectionaryVerse.objects.filter( bible_verse=verse, lection__in=self.lections_where_active())
            for lectionary_verse in verses:
                pairs.update( {(manuscript_id, lectionary_verse.id) for manuscript_id in manuscript_ids} )

        return pairs

    def distinct_bible_verses(self):
        """ Returns a set of all the distinct verses from the lections of this affiliation object. """
        distinct_verses = set()
        for lection in self.lections_where_active():
            distinct_verses.update([v.bible_verse for v in lection.verses.all()])
        return distinct_verses
        
    def distinct_bible_verses_count(self):
        """ Returns the total number of distinct verses from the lections of this affiliation object. """
        return len(self.distinct_bible_verses())
            
    def verse_count(self):
        """ 
        Returns the total number of verses from the lections of this affiliation object.
        
        This may include verses multiple times.
        """
        count = 0
        for lection in self.lections_where_active():
            count += lection.verses.count() # This should be done with an aggregation function in django
        return count
                

class AffiliationLectionarySystem(AffiliationLectionsSet):
    """ An Affiliation class which is active for all lections in a lectionary system (unless specified in an exclusion list). """    
    system = models.ForeignKey(LectionarySystem, on_delete=models.CASCADE)
    exclude = models.ManyToManyField(Lection, blank=True, help_text="All the lections at which this affiliation object is not active.")

    def lections_where_active(self):
        """ All the lections that are included in this affiliation. """
        return self.system.lections.exclude(id__in=self.exclude.values_list( 'id', flat=True ))


class AffiliationLections(AffiliationLectionsSet):
    """ An Affiliation class which is active only in certain lections. """    
    lections = models.ManyToManyField(Lection, blank=True, help_text="All the lections at which this affiliation object is active.")
    
    def lections_where_active(self):
        """ All the lections that are included in this affiliation. """
        return self.lections.all()

    def add_lections( self, lections ):
        """ Adds an iterable of lections to this affiliation object. They can be Lection objects or strings with unique descriptions of the lections. """
        for lection in lections:
            if isinstance(lection, str):
                lection = Lection.objects.filter(description=lection).first()
            if lection and isinstance( lection, Lection ):
                self.lections.add(lection)
        self.save()
                
                
    