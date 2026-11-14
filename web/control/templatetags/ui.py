import json
from django import template
register=template.Library()
@register.filter
def pretty(value):return json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)
@register.filter
def short(value):return str(value or 'unknown')[:12]
@register.filter
def evidence_story(value):
    from resmgrcheck.story import assertion_story
    return assertion_story(value)
