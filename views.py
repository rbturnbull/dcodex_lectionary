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
