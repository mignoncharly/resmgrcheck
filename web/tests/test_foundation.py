from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError,transaction
from control.models import User,Organization,Membership,Project

class FoundationTests(TestCase):
    def test_real_postgres_health_and_migrations(self):
        from django.db import connection
        self.assertEqual(connection.vendor,'postgresql')
        self.assertEqual(self.client.get('/healthz/').json(),{'status':'alive'})
        self.assertEqual(self.client.get('/readyz/').json(),{'status':'ready'})
        self.assertEqual(self.client.post('/healthz/').status_code,405)
    def test_identity_constraints_and_password_hash(self):
        user=User.objects.create_user('Owner@EXAMPLE.TEST','A test password with enough entropy 5187')
        self.assertEqual(user.email,'owner@example.test')
        self.assertTrue(user.password.startswith('argon2'))
        with self.assertRaises(IntegrityError),transaction.atomic():User.objects.create_user('OWNER@example.test','Another password 2815')
    def test_real_tenant_records_are_empty_without_signup(self):
        self.assertEqual(Organization.objects.count(),0)
        user=User.objects.create_user('owner@example.test','Another strong password 8173')
        organization=Organization.objects.create(name='Actual test organization')
        Membership.objects.create(organization=organization,user=user,role='owner')
        Project.objects.create(organization=organization,name='Native checks',created_by=user)
        self.assertEqual(organization.project_set.count(),1)
    def test_server_rendered_staging_shell(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'ResMgrCheck')
        self.assertNotContains(response,'42 runs')
