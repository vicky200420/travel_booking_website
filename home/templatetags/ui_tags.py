from django import template

register = template.Library()


@register.filter
def url_query(value):
    """Return a URL query string from a QueryDict, dropping the `page` key."""
    if hasattr(value, 'urlencode'):
        qs = value.copy()
        qs.pop('page', None)
        return qs.urlencode()
    pairs = [(k, v) for k, v in (value or {}).items() if k != 'page']
    return '&'.join(f'{k}={v}' for k, v in pairs)
