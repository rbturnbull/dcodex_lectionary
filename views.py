from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from dcodex_lectionary.models import *
from dcodex.util import get_request_dict
import logging
import json

@login_required
def lection_verses(request):
    request_dict = get_request_dict(request)

    lection = get_object_or_404(Lection, id=request_dict.get('lection_id'))   
    verse   = LectionaryVerse.objects.filter( id=request_dict.get('verse_id') ).first()
    field_id = request_dict.get('field_id')
    field_class = request_dict.get('field_class')
    
    return render(request, 'dcodex_lectionary/lection_verses.html', {'lection': lection, 'verse': verse, 'field_id':field_id , 'field_class':field_class} )

@login_required
def insert_lection(request):
    request_dict = get_request_dict(request)

    date         = get_object_or_404(FixedDate, id=request_dict.get('date_id'))   
    lection      = get_object_or_404(Lection, id=request_dict.get('lection_id'))   
    manuscript   = get_object_or_404(Manuscript, id=request_dict.get('manuscript_id'))   
    insert_after_lection = get_object_or_404(Lection, id=request_dict.get('insert_after_lection_id'))   
    
    system = manuscript.system
    
    if system is None:
        return Http404("The manuscript '%s' does not have a lectionary system." % manuscript)

    membership = system.insert_lection( date, lection, insert_after=insert_after_lection )
    system.maintenance()
    
    return JsonResponse({ 'first_verse_id':lection.first_verse_id,} );
@login_required
def create_lection(request):
    request_dict = get_request_dict(request)

    date         = get_object_or_404(FixedDate, id=request_dict.get('date_id'))   
    manuscript   = get_object_or_404(Manuscript, id=request_dict.get('manuscript_id'))   
    insert_after_lection = get_object_or_404(Lection, id=request_dict.get('insert_after_lection_id'))   

    lection_description = request_dict.get('lection_description');
    overlapping_lection_IDs = json.loads(request_dict.get('overlapping_lection_IDs'))
    overlapping_lections = [Lection.objects.get(id=id) for id in overlapping_lection_IDs]
    lection = Lection.create_from_passages_string( lection_description, overlapping_lections=overlapping_lections, create_verses=True )
    
    system = manuscript.system
    
    if system is None:
        return Http404("The manuscript '%s' does not have a lectionary system." % manuscript)

    membership = system.insert_lection( date, lection, insert_after=insert_after_lection )
    system.maintenance()
    
    return JsonResponse({ 'first_verse_id':lection.first_verse_id,} );

@login_required
def insert_reference(request):
    request_dict = get_request_dict(request)

    date         = get_object_or_404(FixedDate, id=request_dict.get('date_id'))   
    manuscript   = get_object_or_404(Manuscript, id=request_dict.get('manuscript_id'))   
    insert_after_lection = get_object_or_404(Lection, id=request_dict.get('insert_after_lection_id'))   
    
    system = manuscript.system
    
    reference_text_en = request_dict.get('reference_text_en');
    #occasion_text = request_dict.get('occasion_text');
    #occasion_text_en = request_dict.get('occasion_text_en');
    
    reference_membership_id = request_dict.get('reference_membership')
    reference_membership = get_object_or_404(LectionInSystem, id=reference_membership_id) if reference_membership_id else None
    
    if system is None:
        return Http404("The manuscript '%s' does not have a lectionary system." % manuscript)

    membership = system.create_reference( date=date, insert_after=insert_after_lection, reference_text_en=reference_text_en, reference_membership=reference_membership )

    return JsonResponse({ 'first_verse_id': membership.lection.first_verse_id,} );

@login_required
def lection_suggestions(request):
    request_dict = get_request_dict(request)
    
    date = get_object_or_404(FixedDate, id=request_dict.get('date_id'))   
    memberships = LectionInSystem.objects.filter( fixed_date=date ).all()
    
    return render(request, 'dcodex_lectionary/lection_suggestions.html', {'memberships': memberships} )
    
    
@login_required
def add_lection_box(request):
    request_dict = get_request_dict(request)

    manuscript = get_object_or_404(Manuscript, id=request_dict.get('manuscript_id'))   
    movable_days = DayOfYear.objects.all()
    fixed_days = FixedDate.objects.all()
    lections = Lection.objects.all()
    
    lection_in_system = get_object_or_404(LectionInSystem, id=request_dict.get('lection_in_system_id'))
    
    return render(request, 'dcodex_lectionary/add_lection_box.html', {'manuscript': manuscript, 'lection_in_system':lection_in_system, 'movable_days': movable_days, 'fixed_days':fixed_days, 'lections':lections} )

@login_required
def count(request, request_siglum):
    if request_siglum.isdigit():
        manuscript = get_object_or_404(Manuscript, id=request_siglum)            
    else:
        manuscript = get_object_or_404(Manuscript, siglum=request_siglum)    

    df = manuscript.transcribed_count_df()
    
    title = "%s Count" % (str(manuscript.siglum))
    
    return render(request, 'dcodex/table.html', {'table': df.to_html(), 'title':title} )

@login_required
def complete(request, request_sigla, request_lections):
    mss = []
    request_sigla = request_sigla.split(",")
    for siglum in request_sigla:
        ms = Manuscript.objects.filter(siglum=siglum).first()
        if ms:
            mss.append( ms )

    request_lections = request_lections.replace( "_", " " )
    request_lections = request_lections.split("|")
    lections = []
    for description in request_lections:
        lection = Lection.objects.filter(description=description).first()
        if lection:
            lections.append( lection )


    total_transcribed_count = defaultdict(int)
    total_verses_count = 0
    
    columns = ['Lection'] + [ms.siglum for ms in mss]
    
    
    
    df = pd.DataFrame(columns=columns)
    total = 0
    for i, lection in enumerate(lections):
        verses_count = lection.verses.count()
        total_verses_count += verses_count
        
        percentages = []
                    
        for ms in mss:
            transcribed_verses_count = ms.lection_transcribed_count( lection )
            percentages.append( transcribed_verses_count/verses_count*100.0 )
            total_transcribed_count[ms.siglum] += transcribed_verses_count
            total += transcribed_verses_count
        df.loc[i] = [str(lection)] + percentages
    
    def summary( total, total_verses_count ):
        return "%d of %d (%f)" % (total, total_verses_count, total/total_verses_count*100.0 )
        
    df.loc[len(df)] = [summary(total, total_verses_count * len(mss)) ] + [total_transcribed_count[ms.siglum]/total_verses_count*100.0 for ms in mss]
                
    title = "%s Count" % (str(request_sigla))
    
    formatters={ms.siglum: '{:,.1f}'.format for ms in mss}
    
    styled_df = df.style.apply( lambda x: ['background-color: yellow' if value and value > 99 else 'background-color: lightgreen' if value > 0 else '' for value in x],
                  subset=request_sigla).format(formatters)#.apply( 'text-align: center', subset=request_sigla )
    return render(request, 'dcodex/table.html', {'table': styled_df.render(), 'title':title} )    
    
#    return render(request, 'dcodex/table.html', {'table': df.to_html(formatters=formatters), 'title':title} )



@login_required
def similarity(request, request_siglum, comparison_sigla_string):
    if request_siglum.isdigit():
        manuscript = get_object_or_404(Manuscript, id=request_siglum)            
    else:
        manuscript = get_object_or_404(Manuscript, siglum=request_siglum)    

    comparison_mss = []
    comparison_sigla = comparison_sigla_string.split(",")
    for comparison_siglum in comparison_sigla:
        comparison_ms = Manuscript.objects.filter(siglum=comparison_siglum).first()
        if comparison_ms:
            comparison_mss.append( comparison_ms )
    
    df = manuscript.similarity_df(comparison_mss, ignore_incipits=True)
    title = "%s Similarity" % (str(manuscript.siglum))
    threshold = 76.4    
    styled_df = df.style.apply( lambda x: ['font-weight: bold; background-color: yellow' if value and value > threshold else '' for value in x],
                  subset=comparison_sigla)
    return render(request, 'dcodex/table.html', {'table': styled_df.render(), 'title':title} )
    #return render(request, 'dcodex/table.html', {'table': df.to_html(), 'title':title} )


@login_required
def similarity_probabilities(request, request_siglum, comparison_sigla_string):
    if request_siglum.isdigit():
        manuscript = get_object_or_404(Manuscript, id=request_siglum)            
    else:
        manuscript = get_object_or_404(Manuscript, siglum=request_siglum)    

    comparison_mss = []
    comparison_sigla = comparison_sigla_string.split(",")
    for comparison_siglum in comparison_sigla:
        comparison_ms = Manuscript.objects.filter(siglum=comparison_siglum).first()
        if comparison_ms:
            comparison_mss.append( comparison_ms )
    
    df = manuscript.similarity_probabilities_df(comparison_mss, ignore_incipits=True)
    title = "%s Similarity" % (str(manuscript.siglum))
    threshold = 76.4    
    styled_df = df.style.apply( lambda x: ['font-weight: bold; background-color: yellow' if value and value > threshold else '' for value in x],
                  subset=comparison_sigla)
    return render(request, 'dcodex/table.html', {'table': styled_df.render(), 'title':title} )


@login_required
def affiliation_lections(request, affiliation_id, system_id):
    affiliation = get_object_or_404(AffiliationLections, id=affiliation_id)   
    system = get_object_or_404(LectionarySystem, id=system_id)   
    
    return render(request, 'dcodex_lectionary/affiliation_lections.html', {'affiliation': affiliation, 'system': system, } )


@login_required
def affiliation_lections_list(request, affiliation_id, system_id):
    affiliation = get_object_or_404(AffiliationLections, id=affiliation_id)   
    system = get_object_or_404(LectionarySystem, id=system_id)   

    return render(request, 'dcodex_lectionary/affiliation_lections_list.html', {'affiliation': affiliation, 'system': system, } )


@login_required
def toggle_affiliation_lection(request):
    request_dict = get_request_dict(request)

    affiliation = get_object_or_404(AffiliationLections, id=request_dict.get('affiliation_id'))   
    lection = get_object_or_404(Lection, id=request_dict.get('lection_id'))   
    
    if lection in affiliation.lections.all():
        affiliation.lections.remove(lection)
    else:
        affiliation.lections.add(lection)
    return HttpResponse("OK")


