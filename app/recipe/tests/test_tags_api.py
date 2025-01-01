from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def create_tag(user, name):
    return Tag.objects.create(user=user, name=name)


def create_user(email='user@example.com', password='userpass123'):
    return get_user_model().objects.create_user(email=email, password=password)


def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


class PublicTagApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_retrieve_tags_list(self):
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_get_tags_list(self):
        create_tag(user=self.user, name='Dessert')
        create_tag(user=self.user, name='Fruity')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.filter(user=self.user).order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_tags_limited_to_user(self):
        new_user = create_user(
            email='newuser@example.com',
            password='newuserpass123',
        )
        create_tag(user=new_user, name='Dessert')
        tag = create_tag(user=self.user, name='Salty')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], tag.id)
        self.assertEqual(res.data[0]['name'], tag.name)

    def test_update_tag(self):
        tag = create_tag(user=self.user, name='Sweet')
        url = detail_url(tag_id=tag.id)

        payload = {
            'name': 'Fruity',
        }
        res = self.client.patch(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        tag = create_tag(user=self.user, name='Crispy')
        url = detail_url(tag_id=tag.id)

        res = self.client.delete(url)

        tags = Tag.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        tag1 = Tag.objects.create(
            user=self.user,
            name='Dessert',
        )
        tag2 = Tag.objects.create(
            user=self.user,
            name='Spicy',
        )

        r1 = Recipe.objects.create(
            user=self.user,
            title='Cake',
            time_minutes=5,
            price=Decimal('4'),
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title='Biryani',
            time_minutes=7,
            price=Decimal('3'),
        )

        r1.tags.add(tag1)
        r2.tags.add(tag1)

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        params = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_unique_tag_assigned_to_recipes(self):
        tag = Tag.objects.create(
            user=self.user,
            name='Dessert'
        )
        Tag.objects.create(
            user=self.user,
            name='Spicy',
        )

        r1 = Recipe.objects.create(
            user=self.user,
            title='Cake',
            time_minutes=5,
            price=Decimal('4'),
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title='Biryani',
            time_minutes=7,
            price=Decimal('3'),
        )

        r1.tags.add(tag)
        r2.tags.add(tag)

        params = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, params)
        self.assertEqual(len(res.data), 1)
