import numpy as np
import pandas as pd
from scipy.special import expit
import gotoh

from dcodex.models import VerseTranscriptionBase
from dcodex_bible.models import BibleVerse
from .models import Lectionary


def get_system(base_ms, comparison_ms):
    # Get system if it is not explicitly set
    system = None
    if type(base_ms) == Lectionary:
        system = base_ms.system
    else:
        for ms in comparison_ms:
            if type(ms) == Lectionary:
                system = ms.system
                break
    assert system is not None
    return system


def similarity_probabilities_lection( 
    base_ms, 
    lection, 
    comparison_mss, 
    weights=None, 
    gotoh_param=None, 
    prior_log_odds=0.0, 
    ignore_incipits=False, 
    include_probabilities=True 
):
    weights = weights or [0.07124444438506426, -0.2723489152810223, -0.634987796501936, -0.05103656566400282] # From whole dataset
    gotoh_param = gotoh_param or [6.6995597099885345, -0.9209875054657459, -5.097397327423096, -1.3005714416503906] # From PairHMM of whole dataset
    gotoh_totals = np.zeros( (len(comparison_mss),4), dtype=np.int32 )   
    weights = np.asarray(weights)  
    
    for verse_index, verse in enumerate(lection.verses.all()):
        if verse_index == 0 and ignore_incipits:
            continue
        base_transcription = base_ms.normalized_transcription( verse ) if type(base_ms) is Lectionary else base_ms.normalized_transcription( verse.bible_verse )
        if not base_transcription:
            continue
        
        for ms_index, ms in enumerate(comparison_mss):
            comparison_transcription = ms.normalized_transcription( verse ) if type(ms) is Lectionary else ms.normalized_transcription( verse.bible_verse )
            if not comparison_transcription:
                continue

            counts = gotoh.counts( base_transcription, comparison_transcription, *gotoh_param )
            gotoh_totals[ms_index][:] += counts

    results = []        
    for ms_index in range(len(comparison_mss)):
        length = gotoh_totals[ms_index].sum()            
        similarity = 100.0 * gotoh_totals[ms_index][0]/length if length > 0 else np.NAN
        
        if include_probabilities:
            logodds = prior_log_odds + np.dot( gotoh_totals[ms_index], weights )
            posterior_probability = expit( logodds )
            results.extend([similarity, posterior_probability])
        else:
            if similarity == np.NAN or length == 0:
                similarity = None
            results.append(similarity)
            import logging
            logging.error(f"{similarity =}")
                    
    return results


def similarity_probabilities_df( system, base_ms, comparison_mss, min_verses=2, **kwargs ):
    columns = ['Lection','Lection_Membership__id','Lection_Membership__order']
    for ms in comparison_mss:
        columns.extend( [ms.siglum + "_similarity", ms.siglum + "_probability"] )
    
    df = pd.DataFrame(columns=columns)
    index = 0
    for lection_in_system in system.lections_in_system().all():
        lection = lection_in_system.lection
        if lection.verses.count() < min_verses:
            continue

#            if ignore_untranscribed and self.lection_transcribed_count( lection ) == 0:
#                print("Ignoring untranscribed lection:", lection)
#                continue
        
        results = similarity_probabilities_lection( base_ms, lection, comparison_mss, **kwargs )
            
        df.loc[index] = [str(lection_in_system), lection_in_system.id, lection_in_system.order] + results
        index += 1

    print('similarity_probabilities_df indexes:', index)
    return df      


def similarity_dict( base_ms, comparison_mss, system=None, min_verses = 2, ignore_unstranscribed=True, **kwargs ):
    if system is None:
        system = get_system(base_ms, comparison_mss)

    similarity_dict = dict()
    for lection_in_system in system.lections_in_system().all():

        lection = lection_in_system.lection
        if lection.verses.count() < min_verses:
            continue
            
        if isinstance(base_ms,Lectionary):
            verses = lection.verses.all()
        else:
            verse_ids = lection.verses.exclude(bible_verse=None).values_list('bible_verse__id', flat=True)
            verses = BibleVerse.objects.filter(id__in=verse_ids)

        if VerseTranscriptionBase.objects.filter(manuscript=base_ms, verse__in=verses).count() < min_verses:
            continue

        results = similarity_lection( base_ms, lection, comparison_mss, **kwargs )
        similarity_dict[ lection_in_system ] = dict(zip( comparison_mss, results ))
    return similarity_dict


def similarity_lection( base_ms, lection, comparison_mss, ignore_incipits=False ):
    return similarity_probabilities_lection(base_ms, lection, comparison_mss, ignore_incipits=ignore_incipits, include_probabilities=False)
