from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Split a string into a list by delimiter"""
    if value:
        return value.split(delimiter)
    return []
