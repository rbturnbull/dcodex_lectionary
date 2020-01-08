from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from dcodex_lectionary.models import *
from dcodex.util import get_request_dict

@login_required
def lection_verses(request):
    request_dict = get_request_dict(request)

    lection = get_object_or_404(Lection, id=request_dict.get('lection_id'))   
    verse   = LectionaryVerse.objects.filter( id=request_dict.get('verse_id') ).first()
    field_id = request_dict.get('field_id')
    field_class = request_dict.get('field_class')
    
    return render(request, 'dcodex_lectionary/lection_verses.html', {'lection': lection, 'verse': verse, 'field_id':field_id , 'field_class':field_class} )

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
    
    formatters={ms.siglum: '{:,.1f}%'.format for ms in mss}
    
    return render(request, 'dcodex/table.html', {'table': df.to_html(formatters=formatters), 'title':title} )



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
    threshold = 0.764    
    styled_df = df.style.apply( lambda x: ['font-weight: bold; background-color: yellow' if value and value > threshold else '' for value in x],
                  subset=comparison_sigla)
    return render(request, 'dcodex/table.html', {'table': styled_df.render(), 'title':title} )
    #return render(request, 'dcodex/table.html', {'table': df.to_html(), 'title':title} )
