from django import template
import logging
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def affiliation_active_for(affiliation, lection):
    if lection in affiliation.lections.all():
        return "active"
    return ""

@register.filter
def affiliation_button_for(affiliation, lection):
    if lection in affiliation.lections.all():
        icon = "fa-ban"
        classes = "btn-outline-danger lection"
    else:
        icon = "fa-plus"
        classes = "btn-outline-success lection"

    return mark_safe(f'<button type="button" class="btn {classes}" data-lection="{lection.id}"><i class="fas {icon}"></i></button>')

@register.filter
def list_if_active(affiliation, membership):
    if membership.lection in affiliation.lections.all():
        day_description = membership.day_description()
        return mark_safe(f'<li class="list-group-item lection" data-lection="{membership.lection.id}">\\item {membership.lection} ({day_description})</li>')
    return ""
