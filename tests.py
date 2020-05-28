from django.test import TestCase


from dcodex.models import *
from dcodex_bible.models import *
from dcodex_lectionary.models import *

def mk_easter_lection():
    start_rank = book_names.index('John') * 100
    bible_verses = [BibleVerse(book=book_names.index('John'), chapter=1, verse=i, rank=start_rank+i) for i in range(1,17+1)]
    for verse in bible_verses: verse.save()
    
    lection = Lection.update_or_create_from_passages_string( "Jn 1:1–17", create_verses=True)
    return lection

def mk_great_saturday_lection():
    start_rank = book_names.index('Matthew') * 100
    bible_verses = [BibleVerse(book=book_names.index('Matthew'), chapter=28, verse=i, rank=start_rank+i) for i in range(1,20+1)]
    for verse in bible_verses: verse.save()
    
    lection = Lection.update_or_create_from_passages_string( "Mt 28:1–20", create_verses=True)
    return lection
        


# Create your tests here.
class LectionaryTests(TestCase):
    def test_make_lection(self):
        """
        tests making a lection
        """
        easter_lection = mk_easter_lection()
#        for x in easter_lection.verses.all(): print(x)
        great_saturday_lection = mk_great_saturday_lection()
#        for x in great_saturday_lection.verses.all(): print(x)

        
        self.assertEquals( str(easter_lection), "Jn 1:1–17" )
        self.assertIs( easter_lection.verses.count(), 17 )
        self.assertEquals( str(great_saturday_lection), "Mt 28:1–20" )
        self.assertIs( great_saturday_lection.verses.count(), 20 )

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


        easter_lection = mk_easter_lection()
        great_saturday_lection = mk_great_saturday_lection()

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


        easter_lection = mk_easter_lection()
        great_saturday_lection = mk_great_saturday_lection()

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
    
