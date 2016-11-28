from django.test import TestCase
from django.core.management import call_command

from ovp_users.models import User
from ovp_projects.models import Project
from ovp_organizations.models import Organization
from ovp_core.models import GoogleAddress, Cause, Skill
from ovp_search.helpers import whoosh_raw

from haystack.query import SearchQuerySet


class AddressTestCase(TestCase):
  """
    RealTimeSignalProcessor handles updates to a index tied to a model

    We need to be able to detect changes to a model a rebuild another index,
    such as detecting changes to GoogleAddress and updating the index
    for projects and organizations.

    This is what this class tests.

  """
  def setUp(self):
    call_command('clear_index', '--noinput', verbosity=0)

    self.user = User.objects.create_user(email="testmail@test.com", password="test_returned")
    self.user.save()

    self.address1 = GoogleAddress(typed_address="São paulo, SP - Brazil")
    self.address1.save()

  def test_project_index_on_address_update(self):
    """ Test project index gets reindexed if address changes """
    self.assertTrue(SearchQuerySet().models(Project).all().count() == 0)

    project = Project(name="test project", slug="test-slug", details="abc", description="abc", owner=self.user, address=self.address1, published=True)
    project.save()

    self.assertTrue(SearchQuerySet().models(Project).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Project).filter(address_components__exact=whoosh_raw("São Paulo-locality")).count() == 1)

    project.address.typed_address = "Campinas, SP - Brazil"
    project.address.save()

    self.assertTrue(SearchQuerySet().models(Project).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Project).filter(address_components__exact=whoosh_raw("Campinas-locality")).count() == 1)


  def test_organization_index_on_address_update(self):
    """ Test organization index gets reindexed if address changes """
    self.assertTrue(SearchQuerySet().models(Organization).all().count() == 0)


    organization = Organization(name="test organization", details="abc", owner=self.user, address=self.address1, published=True, type=0)
    organization.save()

    self.assertTrue(SearchQuerySet().models(Organization).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Organization).filter(address_components__exact=whoosh_raw("São Paulo-locality")).count() == 1)

    organization.address.typed_address = "Campinas, SP - Brazil"
    organization.address.save()

    self.assertTrue(SearchQuerySet().models(Organization).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Organization).filter(address_components__exact=whoosh_raw("Campinas-locality")).count() == 1)


class ProjectIndexTestCase(TestCase):
  def setUp(self):
    call_command('clear_index', '--noinput', verbosity=0)

    self.user = User.objects.create_user(email="testmail@test.com", password="test_returned")
    self.user.save()

    self.address1 = GoogleAddress(typed_address="São paulo, SP - Brazil")
    self.address1.save()
    self.address2 = GoogleAddress(typed_address="Campinas, SP - Brazil")
    self.address2.save()

  def test_index_on_create_and_update(self):
    """ Test project index gets updated when a project is created or updated """
    self.assertTrue(SearchQuerySet().models(Project).all().count() == 0)

    project = Project(name="test project", slug="test-slug", details="abc", description="abc", owner=self.user, address=self.address1, published=True)
    project.save()

    self.assertTrue(SearchQuerySet().models(Project).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Project).filter(address_components__exact=whoosh_raw("São Paulo-locality")).count() == 1)

    project.address = self.address2
    project.save()

    self.assertTrue(SearchQuerySet().models(Project).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Project).filter(address_components__exact=whoosh_raw("Campinas-locality")).count() == 1)


  def test_index_on_causes_update(self):
    """ Test project index gets updated when a cause is modified """
    cause = Cause.objects.all().order_by('pk')[0]
    project = Project(name="test project", slug="test-slug", details="abc", description="abc", owner=self.user, address=self.address1, published=True)
    project.save()

    self.assertTrue(SearchQuerySet().models(Project).filter(causes=cause.pk).count() == 0)

    project.causes.add(cause)

    self.assertTrue(SearchQuerySet().models(Project).filter(causes=cause.pk).count() == 1)


  def test_index_on_skill_update(self):
    """ Test project index gets updated when a skill is modified """
    skill = Skill.objects.all().order_by('pk')[0]
    project = Project(name="test project", slug="test-slug", details="abc", description="abc", owner=self.user, address=self.address1, published=True)
    project.save()

    self.assertTrue(SearchQuerySet().models(Project).filter(skills=skill.pk).count() == 0)

    project.skills.add(skill)

    self.assertTrue(SearchQuerySet().models(Project).filter(skills=skill.pk).count() == 1)


class OrganizationIndexTestCase(TestCase):
  def setUp(self):
    call_command('clear_index', '--noinput', verbosity=0)

    self.user = User.objects.create_user(email="testmail@test.com", password="test_returned")
    self.user.save()

    self.address1 = GoogleAddress(typed_address="São paulo, SP - Brazil")
    self.address1.save()
    self.address2 = GoogleAddress(typed_address="Campinas, SP - Brazil")
    self.address2.save()

  def test_index_on_create_and_update(self):
    """ Test organization index gets updated when a project is created or updated """
    self.assertTrue(SearchQuerySet().models(Project).all().count() == 0)

    organization = Organization(name="test organization", details="abc", owner=self.user, address=self.address1, published=True, type=0)
    organization.save()

    self.assertTrue(SearchQuerySet().models(Organization).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Organization).filter(address_components__exact=whoosh_raw("São Paulo-locality")).count() == 1)

    organization.address = self.address2
    organization.save()

    self.assertTrue(SearchQuerySet().models(Organization).all().count() == 1)
    self.assertTrue(SearchQuerySet().models(Organization).filter(address_components__exact=whoosh_raw("Campinas-locality")).count() == 1)


  def test_index_on_causes_update(self):
    """ Test organization index gets updated when a cause is modified """
    cause = Cause.objects.all().order_by('pk')[0]
    organization = Organization(name="test organization", details="abc", owner=self.user, address=self.address1, published=True, type=0)
    organization.save()

    self.assertTrue(SearchQuerySet().models(Organization).filter(causes=cause.pk).count() == 0)

    organization.causes.add(cause)

    self.assertTrue(SearchQuerySet().models(Organization).filter(causes=cause.pk).count() == 1)