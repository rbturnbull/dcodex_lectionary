from django.db import models
from django.db.models import Max, Min, Sum
from dcodex.models import Manuscript, Verse
from dcodex_bible.models import BibleVerse
from django.shortcuts import render
from itertools import chain
import numpy as np
import pandas as pd
import dcodex.distance as distance
from collections import defaultdict

import logging

class LectionaryVerse(Verse):
    bible_verse = models.ForeignKey(BibleVerse, on_delete=models.CASCADE)
    unique_string = models.CharField(max_length=20, default="")
    
    def reference(self, abbreviation = False, end_verse=None):
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

    @classmethod
    def new_from_bible_verse( cls, bible_verse ):
        unique_string = bible_verse.reference_abbreviation().replace(" ", '')
        count = LectionaryVerse.objects.filter( unique_string=unique_string ).count()
        if count > 0:
            unique_string += "_%d" % (count+1)

        try:
            rank = 1 + cls.objects.aggregate( Max('rank') )['rank__max']
        except:
            rank = 1

        lectionary_verse = cls( bible_verse=bible_verse, rank=rank, unique_string=unique_string)
        lectionary_verse.save()
        return lectionary_verse

    @classmethod
    def new_from_bible_verse_id( cls, bible_verse_id ):
        bible_verse = BibleVerse.objects.get( id=bible_verse_id )    
        return cls.new_from_bible_verse( bible_verse )





class Lection(models.Model):
    verses = models.ManyToManyField(LectionaryVerse)
    description = models.CharField(max_length=100)
        
    def __str__(self):
        return self.description


    def add_verses_from_range( self, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):
        lection_bible_verse_start = BibleVerse.get_from_string( start_verse_string )
        lection_bible_verse_end   = BibleVerse.get_from_string( end_verse_string )   
        
        # Find verses in other lections to use for this lection
        verses_from_other_lections = []
        for lection_description_with_verses in lection_descriptions_with_verses:
            print("Finding lection:", lection_description_with_verses)
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
    

    @classmethod
    def update_or_create_from_description( cls, description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):
        lection, created = cls.objects.get_or_create(description=description)
        if created == False:
            return lection

        lection.verses.clear()  
        lection.add_verses_from_range( start_verse_string, end_verse_string, lection_descriptions_with_verses, create_verses )
    
        return lection    
    def first_verse(self):
        return self.verses.first()

    def calculate_mass(self):
        mass = self.verses.aggregate( Sum('bible_verse__char_count') ).get('bible_verse__char_count__sum')
        return mass
    
class FixedDate(models.Model):
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
        
        return string
    class Meta:
        verbose_name_plural = 'Days of year'        

    
class LectionInSystem(models.Model):
    lection = models.ForeignKey(Lection, on_delete=models.CASCADE)
    system  = models.ForeignKey('LectionarySystem', on_delete=models.CASCADE)
    day_of_year = models.ForeignKey(DayOfYear, on_delete=models.CASCADE, default=None, null=True)
    fixed_date = models.ForeignKey(FixedDate, on_delete=models.CASCADE, default=None, null=True)
    order_on_day = models.IntegerField(default=0)
    cumulative_mass_lections = models.IntegerField(default=-1) # The mass of all the previous lections until the start of this one
    
    def __str__(self):
        return "%s in %s on %s" % ( str(self.lection), str(self.system), str(self.day_of_year) )
        
    def day_description(self):
        if self.order_on_day < 2:
            return str(self.day_of_year)
        return "%s %d" % (str(self.day_of_year), self.order_on_day)
        
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
        ordering = ['fixed_date', 'day_of_year', 'order_on_day',]
        
    def prev(self):
        return self.system.prev_lection_in_system( self )
    def next(self):
        return self.system.next_lection_in_system( self )
    def cumulative_mass_of_verse( self, verse ):
        mass = self.cumulative_mass_lections
        cumulative_mass_verses = self.lection.verses.filter( rank__lt=verse.rank ).aggregate( Sum('bible_verse__char_count') ).get('bible_verse__char_count__sum')
        if cumulative_mass_verses:
            mass += cumulative_mass_verses
        return mass
    
class LectionarySystem(models.Model):
    name = models.CharField(max_length=200)
    lections = models.ManyToManyField(Lection, through=LectionInSystem)
    def __str__(self):
        return self.name    
    def first_verse(self):
        return self.lections_in_system().first().lection.verses.first()
        
    def lections_in_system(self):
        return LectionInSystem.objects.filter(system=self)   
        
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
            cumulative_mass += lection_in_system.lection.calculate_mass()

    @classmethod
    def calculate_masses_all_systems( cls ):
        for system in cls.objects.all():
            system.calculate_masses()
    
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
        
    def add_lection( self, day_of_year, lection ):
        membership, created = LectionInSystem.objects.get_or_create(system=self, lection=lection, day_of_year=day_of_year)    
        membership.save()
        return membership
      
    def add_lection_from_description( self, day_of_year, lection_description ):
        lection, created = Lection.objects.get_or_create(description=lection_description)
        return self.add_lection( day_of_year, lection )
        
    def add_new_lection_from_description( self, day_of_year, lection_description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):        
        lection = Lection.update_or_create_from_description(description=lection_description, start_verse_string=start_verse_string, end_verse_string=end_verse_string, lection_descriptions_with_verses=lection_descriptions_with_verses, create_verses=create_verses)    
        return self.add_lection( day_of_year, lection )
       
    def delete_all_on_day( self, day_of_year ):
        print("Deleting all on Day of year:", day_of_year )
        lection_memberships = LectionInSystem.objects.filter(system=self, day_of_year=day_of_year).delete()
            
    def replace_with_lection( self, day_of_year, lection ):
        self.delete_all_on_day( day_of_year )
        print("Adding:", lection)
        return self.add_lection( day_of_year, lection )
        
    def replace_with_new_lection_from_description( self, day_of_year, lection_description, start_verse_string, end_verse_string, lection_descriptions_with_verses=[], create_verses=False ):        
        lection = Lection.update_or_create_from_description(description=lection_description, start_verse_string=start_verse_string, end_verse_string=end_verse_string, lection_descriptions_with_verses=lection_descriptions_with_verses, create_verses=create_verses)    
        self.replace_with_lection( day_of_year, lection )
        return lection

    def empty( self ):
        LectionInSystem.objects.filter( system=self ).delete()
        
    def clone_to_system( self, new_system ):
        new_system.empty()
        for lection_membership in self.lections_in_system().all():
            LectionInSystem.objects.get_or_create(system=new_system, lection=lection_membership.lection, day_of_year=lection_membership.day_of_year)    
    
    def clone_to_system_with_name(self, new_system_name ):
        new_system, created = LectionarySystem.objects.get_or_create(name=new_system_name)
        self.clone_to_system( new_system )
        return new_system

    def cumulative_mass( self, verse ):
        lection_in_system = self.lection_in_system_for_verse( verse )
        if lection_in_system:
            return lection_in_system.cumulative_mass_of_verse( verse )
        return 0
        
        
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
        return render(request, self.verse_search_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system, 'next_verse':self.next_verse(verse), 'prev_verse':self.prev_verse(verse),} )

    # Override
    def render_location_popup( self, request, verse ):
        lection_in_system = self.system.lection_in_system_for_verse( verse )
        return render(request, self.location_popup_template(), {'verse': verse, 'manuscript': self, 'lection_in_system': lection_in_system, 'next_verse':self.next_verse(verse), 'prev_verse':self.prev_verse(verse),} )

    # Override
    def comparison_texts( self, verse, manuscripts = None ):
        lectionary_comparisons = super().comparison_texts( verse, manuscripts )
        continuous_text_comparisons = super().comparison_texts( verse.bible_verse, manuscripts )
        return list(chain(lectionary_comparisons, continuous_text_comparisons))

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
    

    def similarity_lection( self, lection, comparison_mss, similarity_func=distance.similaity_levenshtein, ignore_incipits=False ):

        similarity_values = np.zeros( (len(comparison_mss),) )
        counts = np.zeros( (len(comparison_mss),), dtype=int )
        
        for verse_index, verse in enumerate(lection.verses.all()):
            if verse_index == 0 and ignore_incipits:
                continue
            my_transcription = self.transcription( verse )
            if not my_transcription:
                continue
            
            for ms_index, ms in enumerate(comparison_mss):
                comparison_transcription = ms.transcription( verse ) if type(ms) is Lectionary else ms.transcription( verse.bible_verse )
                if not comparison_transcription:
                    continue
                
                similarity_values[ms_index] += similarity_func( my_transcription.transcription, comparison_transcription.transcription )
                counts[ms_index] += 1

        averages = []
        for similarity_value, count in zip(similarity_values, counts):
            average = None if count == 0 else similarity_value/count
            averages.append(average)
        return averages
                        
    def similarity_df( self, comparison_mss, **kwargs ):
        columns = ['Lection']        
        columns += [ms.siglum for ms in comparison_mss]
        
        df = pd.DataFrame(columns=columns)
        for i, lection_in_system in enumerate(self.system.lections_in_system().all()):
            lection = lection_in_system.lection
            averages = self.similarity_lection( lection, comparison_mss, **kwargs )
                
            df.loc[i] = [str(lection_in_system)] + averages

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
            
            
        


    def cumulative_mass( self, verse ):
        return self.system.cumulative_mass(verse)
        
    def distance_between_verses( self, verse1, verse2 ):
        return self.cumulative_mass( verse2 ) - self.cumulative_mass( verse1 )