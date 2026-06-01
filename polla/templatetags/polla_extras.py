from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def puntos_badge(puntos):
    if puntos == 3:
        return 'success'
    if puntos == 1:
        return 'warning'
    return 'secondary'
