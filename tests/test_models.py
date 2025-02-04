from pathlib import Path
from re import A
from django.test import TestCase

#from model_bakery import baker

from dcodex.models import *
from dcodex_bible.models import *
from imagedeck.models import DeckImage, Deck
from dcodex_lectionary.models import *

def make_easter_lection():
    start_rank = book_names.index('John') * 100
    char_aggregate = BibleVerse.objects.count()
    for i in range(1,17+1):
        BibleVerse.objects.create(
            book=book_names.index('John'), 
            chapter=1, 
            verse=i, 
            rank=start_rank+i, 
            char_aggregate=char_aggregate+i*DEFAULT_LECTIONARY_VERSE_MASS, 
            char_count=DEFAULT_LECTIONARY_VERSE_MASS,
        )     
    lection = Lection.update_or_create_from_passages_string( "Jn 1:1–17", create_verses=True)
    return lection

def make_great_saturday_lection():
    start_rank = book_names.index('Matthew') * 100
    char_aggregate = BibleVerse.objects.count()
    for i in range(1,20+1):
        BibleVerse.objects.create(
            book=book_names.index('Matthew'), 
            chapter=28, 
            verse=i, 
            rank=start_rank+i, 
            char_aggregate=char_aggregate+i*DEFAULT_LECTIONARY_VERSE_MASS, 
            char_count=DEFAULT_LECTIONARY_VERSE_MASS,
        )     
    
    lection = Lection.update_or_create_from_passages_string( "Mt 28:1–20", create_verses=True)
    return lection
        

class LectionTests(TestCase):
    def test_cumulative_mass_from_lection_start(self):
        lection = make_easter_lection()
        for index, verse_membership in enumerate(lection.verse_memberships()):
            self.assertEqual( verse_membership.cumulative_mass_from_lection_start, index*DEFAULT_LECTIONARY_VERSE_MASS )


class LectionaryVerseTests(TestCase):
    def test_get_from_string(self):
        make_great_saturday_lection()
        verse = LectionaryVerse.get_from_string("Mt28:10")
        self.assertIsNotNone( verse )
        self.assertEqual(str(verse), "Matthew 28:10")

    def test_mass(self):
        make_great_saturday_lection()
        verse = LectionaryVerse.get_from_string("Mt28:10")
        self.assertEqual( verse.bible_verse.char_aggregate, 10*DEFAULT_LECTIONARY_VERSE_MASS )
        self.assertEqual( verse.mass, DEFAULT_LECTIONARY_VERSE_MASS )


class LectionaryTests(TestCase):
    def test_make_lection(self):
        """
        tests making a lection
        """
        easter_lection = make_easter_lection()
#        for x in easter_lection.verses.all(): print(x)
        great_saturday_lection = make_great_saturday_lection()
#        for x in great_saturday_lection.verses.all(): print(x)

        
        self.assertEquals( str(easter_lection), "Jn 1:1–17" )
        self.assertIs( easter_lection.verses.count(), 17 )
        self.assertEquals( str(great_saturday_lection), "Mt 28:1–20" )
        self.assertIs( great_saturday_lection.verses.count(), 20 )

    def test_lectionary_first_last_positions(self):
        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        easter, _ = MovableDay.objects.update_or_create( season=MovableDay.EASTER, week=1, day_of_week=MovableDay.SUNDAY )
        great_saturday, _ = MovableDay.objects.update_or_create( season=MovableDay.GREAT_WEEK, week=1, day_of_week=MovableDay.SATURDAY )

        system = LectionarySystem.objects.create(name="Test Lectionary System")
        system.add_lection(easter, easter_lection)
        system.add_lection(great_saturday, great_saturday_lection)

        ms = Lectionary.objects.create(name="Test Lectionary", system=system)
        ms.imagedeck = Deck.objects.create(name="Test Lectionary Imagedeck")
        ms.save()   

        membership1 = ms.imagedeck.add_image( DeckImage.objects.create() )
        membership2 = ms.imagedeck.add_image( DeckImage.objects.create() )
        membership3 = ms.imagedeck.add_image( DeckImage.objects.create() )

        first_location = ms.save_location(easter_lection.verses.first(), membership1, 0.0, 0.0)
        ms.save_location(easter_lection.verses.last(), membership2, 0.0, 0.0)
        last_location = ms.save_location(great_saturday_lection.verses.last(), membership3, 0.0, 0.5)
        ms.save_location(great_saturday_lection.verses.first(), membership3, 0.0, 0.0)

        self.assertEqual( ms.first_location().id, first_location.id)
        self.assertEqual( ms.last_location().id, last_location.id)

    def test_affiliation_lection(self):
        """
        Tests the ability to make an Affiliation from a lection.
        """
        ms = Manuscript(name="Test Lectionary")
        ms.save()        
        family1 = Family(name="Test Family 1")
        family1.save()
        family2 = Family(name="Test Family 2")
        family2.save()


        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        family1.add_manuscript_all( ms )
        
        affiliation = AffiliationLections( name="Great Week Affiliation" )
        family2.add_manuscript_to_affiliation( affiliation, ms )
        affiliation.add_lections( ["Mt 28:1–20"] )        

        self.assertIs( ms.families_at(easter_lection.verses.first()).count(), 1 )
        self.assertIs( ms.families_at(great_saturday_lection.verses.first()).count(), 2 )
        self.assertIs( ms.is_in_family_at(family1, easter_lection.verses.last()), True )
        self.assertIs( ms.is_in_family_at(family2, easter_lection.verses.last()), False )
        self.assertIs( ms.is_in_family_at(family1, great_saturday_lection.verses.last()), True )        
        self.assertIs( ms.is_in_family_at(family2, great_saturday_lection.verses.last()), True )        

        self.assertIs( ms.is_in_family_at(family1, easter_lection.verses.last().bible_verse), True )
        self.assertIs( ms.is_in_family_at(family2, easter_lection.verses.last().bible_verse), False )
        self.assertIs( ms.is_in_family_at(family1, great_saturday_lection.verses.last().bible_verse), True )        
        self.assertIs( ms.is_in_family_at(family2, great_saturday_lection.verses.last().bible_verse), True )        

    def test_affiliation_lection_overlap(self):
        """
        Tests the ability to make an Affiliation from a lection where the groups overlap.
        """
        ms = Manuscript(name="Test Lectionary")
        ms.save()        
        family1 = Family(name="Test Family 1")
        family1.save()
        family2 = Family(name="Test Family 2")
        family2.save()


        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        family1.add_manuscript_all( ms )
        overlap_affiliation = AffiliationLections( name="families 1 & 2 overlap" )
        overlap_affiliation.save()
        overlap_affiliation.families.add( family1 )
        overlap_affiliation.families.add( family2 )
        overlap_affiliation.add_lections( ["Mt 28:1–20"] )
        overlap_affiliation.save()

        self.assertIs( ms.families_at(easter_lection.verses.first()).count(), 1 )
        self.assertIs( ms.families_at(great_saturday_lection.verses.first()).count(), 2 )
        self.assertIs( ms.is_in_family_at(family1, easter_lection.verses.last()), True )
        self.assertIs( ms.is_in_family_at(family2, easter_lection.verses.last()), False )
        self.assertIs( ms.is_in_family_at(family1, great_saturday_lection.verses.last()), True )        
        self.assertIs( ms.is_in_family_at(family2, great_saturday_lection.verses.last()), True )        
    
        self.assertIs( ms.is_in_family_at(family1, easter_lection.verses.last().bible_verse), True )
        self.assertIs( ms.is_in_family_at(family2, easter_lection.verses.last().bible_verse), False )
        self.assertIs( ms.is_in_family_at(family1, great_saturday_lection.verses.last().bible_verse), True )        
        self.assertIs( ms.is_in_family_at(family2, great_saturday_lection.verses.last().bible_verse), True )        
    

class AffiliationLectionsTests(TestCase):
    def setUp(self):
        self.ms = Manuscript(name="Test Lectionary")
        self.ms.save()        
        self.family1 = Family(name="Test Family 1")
        self.family1.save()

        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        overlap_affiliation = AffiliationLections( name="families 1 & 2 overlap" )
        overlap_affiliation.save()
        overlap_affiliation.families.add( self.family1 )
        overlap_affiliation.manuscripts.add( self.ms )
        overlap_affiliation.add_lections( ["Mt 28:1–20"] )
        overlap_affiliation.save()

    def test_manuscript_and_verse_ids_at(self):
        bible_verse = BibleVerse.get_from_string( "Mt 28:1" )
        pairs = list(self.family1.manuscript_and_verse_ids_at( bible_verse ))
        self.assertEqual( len(pairs), 1 )
        manuscript_id = pairs[0][0]
        verse_id = pairs[0][1]
        self.assertEqual( manuscript_id, self.ms.id )
        found_verse = Verse.objects.get(id=verse_id)
        self.assertEqual( manuscript_id, self.ms.id )
        self.assertIs(type(found_verse), LectionaryVerse)
        self.assertEqual(found_verse.bible_verse.id, bible_verse.id)

    def test_manuscript_and_verse_ids_at_none(self):
        bible_verse = BibleVerse.get_from_string( "Jn 1:1" )
        pairs = list(self.family1.manuscript_and_verse_ids_at( bible_verse ))
        self.assertEqual( len(pairs), 0 )


class AffiliationLectionarySystemTests(TestCase):
    def setUp(self):
        self.ms = Manuscript(name="Test Lectionary")
        self.ms.save()        
        self.system = LectionarySystem(name="Test Lectionary System")
        self.system.save()
        self.family1 = Family(name="Test Family 1")
        self.family1.save()

        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        self.system.lections.add( easter_lection )


        affiliation = AffiliationLectionarySystem( name="Test AffiliationLectionarySystem", system=self.system )
        affiliation.save()
        affiliation.families.add( self.family1 )
        affiliation.manuscripts.add( self.ms )
        affiliation.save()

    def test_manuscript_and_verse_ids_at(self):
        bible_verse = BibleVerse.get_from_string( "Jn 1:1" )
        pairs = list(self.family1.manuscript_and_verse_ids_at( bible_verse ))
        self.assertEqual( len(pairs), 1 )
        manuscript_id = pairs[0][0]
        verse_id = pairs[0][1]
        self.assertEqual( manuscript_id, self.ms.id )
        found_verse = Verse.objects.get(id=verse_id)
        self.assertEqual( manuscript_id, self.ms.id )
        self.assertIs(type(found_verse), LectionaryVerse)
        self.assertEqual(found_verse.bible_verse.id, bible_verse.id)

    def test_manuscript_and_verse_ids_at_none(self):
        bible_verse = BibleVerse.get_from_string( "Mt 28:1" )
        pairs = list(self.family1.manuscript_and_verse_ids_at( bible_verse ))
        self.assertEqual( len(pairs), 0 )


class MovableDayTests(TestCase):
    def test_read_season(self):
        self.assertEquals( MovableDay.read_season("Easter"), MovableDay.EASTER )
        self.assertEquals( MovableDay.read_season("EAST"), MovableDay.EASTER )
        self.assertEquals( MovableDay.read_season("Pent"), MovableDay.PENTECOST )
        self.assertEquals( MovableDay.read_season("Pentecost"), MovableDay.PENTECOST )
        self.assertEquals( MovableDay.read_season("Feast"), MovableDay.FEAST_OF_THE_CROSS )
        self.assertEquals( MovableDay.read_season("Great Week "), MovableDay.GREAT_WEEK )
        self.assertEquals( MovableDay.read_season("L"), MovableDay.LENT )
        self.assertEquals( MovableDay.read_season("EPIPH"), MovableDay.EPIPHANY )
        self.assertEquals( MovableDay.read_season("Theophany"), MovableDay.EPIPHANY )
        self.assertEquals( MovableDay.read_season("cross"), MovableDay.FEAST_OF_THE_CROSS )

    def test_read_day(self):
        self.assertEquals( MovableDay.read_day_of_week("Sunday"), MovableDay.SUNDAY )
        self.assertEquals( MovableDay.read_day_of_week("sun"), MovableDay.SUNDAY )
        self.assertEquals( MovableDay.read_day_of_week("Tues"), MovableDay.TUESDAY )


class LectionarySystemTests(TestCase):
    def setUp(self):
        self.system = LectionarySystem(name="Test Lectionary System")
        self.system.save()

    def test_import_csv_incomplete(self):
        csv = Path(__file__).parent/"testdata/test-system-incomplete.csv"
        with self.assertRaises(ValueError):
            self.system.import_csv( csv )
        
    def test_import_csv_incorrect_date(self):
        csv = Path(__file__).parent/"testdata/test-system-incorrect-date.csv"
        with self.assertRaises(ValueError):
            self.system.import_csv( csv )
        
    def test_import_csv(self):
        # Create Days
        easter, _ = MovableDay.objects.update_or_create( season=MovableDay.EASTER, week=1, day_of_week=MovableDay.SUNDAY )
        great_saturday, _ = MovableDay.objects.update_or_create( season=MovableDay.GREAT_WEEK, week=1, day_of_week=MovableDay.SATURDAY )
        gold_days = [easter, great_saturday]
        gold_lections = [make_easter_lection(), make_great_saturday_lection()]

        csv = Path(__file__).parent/"testdata/test-system.csv"
        self.system.import_csv( csv )

        self.assertEquals( self.system.lections.count(), 2 )
        
        lection_memberships = list(self.system.lections_in_system())
        for membership, gold_day, gold_lection in zip(lection_memberships, gold_days, gold_lections):
            self.assertEquals( membership.day.id, gold_day.id)
            self.assertEquals( membership.lection.id, gold_lection.id)

    def test_dataframe(self):
        easter, _ = MovableDay.objects.update_or_create( season=MovableDay.EASTER, week=1, day_of_week=MovableDay.SUNDAY )
        great_saturday, _ = MovableDay.objects.update_or_create( season=MovableDay.GREAT_WEEK, week=1, day_of_week=MovableDay.SATURDAY )
        gold_days = [easter, great_saturday]
        gold_lections = [make_easter_lection(), make_great_saturday_lection()]

        for day, lection in zip(gold_days, gold_lections):
            self.system.add_lection( day, lection )

        df = self.system.dataframe()
        gold_columns = ['lection', 'season', 'week', 'day']
        self.assertListEqual( gold_columns, list(df.columns) )
        self.assertEquals( len(df.index), 2 )


class FixtureTests(TestCase):
    fixtures = ["lectionarydays.json"]

    def test_moveable_days(self):
        self.assertEqual( MovableDay.objects.filter( season=MovableDay.EASTER, week=1, day_of_week=MovableDay.SUNDAY ).count(), 1 )
        self.assertEqual( MovableDay.objects.filter( season=MovableDay.PENTECOST, week=1, day_of_week=MovableDay.MONDAY ).count(), 1 )


class LectionaryLocationTests(TestCase):

    def setUp(self):
        easter_lection = make_easter_lection()
        great_saturday_lection = make_great_saturday_lection()

        easter, _ = MovableDay.objects.update_or_create( season=MovableDay.EASTER, week=1, day_of_week=MovableDay.SUNDAY )
        great_saturday, _ = MovableDay.objects.update_or_create( season=MovableDay.GREAT_WEEK, week=1, day_of_week=MovableDay.SATURDAY )

        system = LectionarySystem.objects.create(name="Test Lectionary System")
        system.add_lection(easter, easter_lection)
        system.add_lection(great_saturday, great_saturday_lection)
        system.maintenance()

        self.ms = Lectionary.objects.create(name="Test Lectionary", system=system)
        self.ms.imagedeck = Deck.objects.create(name="Test Lectionary Imagedeck")
        self.ms.save()   

        self.membership1 = self.ms.imagedeck.add_image( DeckImage.objects.create() )
        self.membership2 = self.ms.imagedeck.add_image( DeckImage.objects.create() )
        self.membership3 = self.ms.imagedeck.add_image( DeckImage.objects.create() )

        self.first_location = self.ms.save_location(easter_lection.verses.first(), self.membership1, 0.0, 0.0)
        self.ms.save_location(easter_lection.verses.last(), self.membership2, 0.0, 0.0)
        verse = LectionaryVerse.get_from_string("Mt28:10")
        self.last_location = self.ms.save_location(verse, self.membership3, 0.0, 0.5)
        verse = LectionaryVerse.get_from_string("Mt28:1")
        self.ms.save_location(verse, self.membership3, 0.0, 0.0)

    def test_lectionary_first_position(self):
        self.assertEqual( self.ms.first_location().id, self.first_location.id)

    def test_lectionary_first_position(self):
        self.assertEqual( self.ms.last_location().id, self.last_location.id)    

    def test_lectionary_extrapolate(self):
        location = self.ms.location( LectionaryVerse.get_from_string("Mt28:20") )
        self.assertEqual( location.id, None )    
        self.assertIsNotNone( location.deck_membership )    
        self.assertEqual( location.deck_membership.id, self.membership3.id )
        self.assertEqual( location.y, 1.0 )
