from ovp_search import helpers
from haystack.query import SQ

from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import NotAuthenticated

from django.db.models import When, F, IntegerField, Count, Case

import json

#####################
## ViewSet filters ##
#####################

class ProjectRelevanceOrderingFilter(OrderingFilter):
  def get_skills_and_causes(self, request):
    if not request.user.is_authenticated():
      raise NotAuthenticated()

    user = request.user
    output = {"skills": [], "causes": []}

    if user.profile:
      output["skills"] = user.profile.skills.values_list('id', flat=True)
      output["causes"] = user.profile.causes.values_list('id', flat=True)

    return output

  def annotate_queryset(self, queryset, request):
    self.get_skills_and_causes(request)

    queryset = queryset\
                .annotate(\
                  cause_relevance =
                    Count(
                      Case(When(causes__pk__in=[1,3], then=1),
                           output_field=IntegerField()),
                      distinct=True),
                  skill_relevance =
                    Count(
                      Case(When(skills__pk__in=[1,2,4], then=1),
                                output_field=IntegerField()),
                      distinct=True))\
                .annotate(relevance = F('cause_relevance') + F('skill_relevance'))

    return queryset

  def filter_queryset(self, request, queryset, view):
    ordering = self.get_ordering(request, queryset, view)

    if ordering:
      if "relevance" in ordering or "-relevance" in ordering:
        queryset = self.annotate_queryset(queryset, request)

    if ordering:
      return queryset.order_by(*ordering)

    return queryset


######################
## Haystack filters ##
######################

def get_operator_and_items(string=''):
  items = string.split(',')

  if items[0] == "AND" or items[0] == "OR":
    first = items.pop(0)

    if first == "AND":
      return SQ.AND, items
    if first == "OR":
      return SQ.OR, items

  return SQ.OR, items

def by_skills(queryset, skill_string=None):
  """ Filter queryset by a comma delimeted skill list """
  if skill_string:
    operator, items = get_operator_and_items(skill_string)
    q_obj = SQ()
    for s in items:
      if len(s) > 0:
        q_obj.add(SQ(skills=s), operator)
    queryset = queryset.filter(q_obj)
  return queryset


def by_causes(queryset, cause_string=None):
  """ Filter queryset by a comma delimeted cause list """
  if cause_string:
    operator, items = get_operator_and_items(cause_string)
    q_obj = SQ()
    for c in items:
      if len(c) > 0:
        q_obj.add(SQ(causes=c), operator)
    queryset = queryset.filter(q_obj)
  return queryset


def by_published(queryset, published_string='true'):
  """ Filter queryset by publish status """
  if published_string == 'true':
    queryset = queryset.filter(published=1)
  elif published_string == 'false':
    queryset = queryset.filter(published=0)
  # Any other value will return both published and unpublished
  return queryset


def by_name(queryset, name=None):
  """ Filter queryset by name, with word wide auto-completion """
  if name:
    queryset = queryset.filter(name=name)
  return queryset


def by_address(queryset, address='', project=False):
  """
  Filter queryset by publish status.

  If project=True, we also apply a project exclusive filter
  """
  if address:
    address = json.loads(address)
    if u'address_components' in address:
      q_objs = []

      """
      Caribbean filter
      """
      if len(address[u'address_components']):
        if address[u'address_components'][0]['long_name'] == 'Caribbean':
          queryset = queryset.filter(
            SQ(address_components=helpers.whoosh_raw(u"{}-{}".format('Jamaica', 'country').strip())) |
            SQ(address_components=helpers.whoosh_raw(u"{}-{}".format('Haiti', 'country').strip())) |
            SQ(address_components=helpers.whoosh_raw(u"{}-{}".format('Saint Lucia', 'country').strip())) |
            SQ(address_components=helpers.whoosh_raw(u"{}-{}".format('Suriname', 'country').strip())) |
            SQ(address_components=helpers.whoosh_raw(u"{}-{}".format('Trinidad & Tobago', 'country').strip()))
          )

          return queryset

        for component in address[u'address_components']:
          q_obj = SQ()
          test = ''

          for component_type in component[u'types']:
            type_string = helpers.whoosh_raw(u"{}-{}".format(component[u'long_name'], component_type).strip())
            q_obj.add(SQ(address_components=type_string), SQ.OR)

          q_objs.append(q_obj)

        # Filter all address components
        for obj in q_objs:
          queryset = queryset.filter(obj)
      else: # remote projects
        if project:
          queryset = queryset.filter(can_be_done_remotely=1)
  return queryset

def filter_out(queryset, setting_name):
  """
  Remove unwanted results from queryset
  """
  kwargs = helpers.get_settings().get(setting_name, {}).get('FILTER_OUT', {})
  queryset = queryset.exclude(**kwargs)
  return queryset
