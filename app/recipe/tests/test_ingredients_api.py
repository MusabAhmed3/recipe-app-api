from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='user@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)


def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_get_ingredients_list(self):
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_ingredients_list(self):
        Ingredient.objects.create(user=self.user, name='Salt')
        Ingredient.objects.create(user=self.user, name='Sugar')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredients = Ingredient.objects.filter(
            user=self.user,
        ).order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_get_ingredients_limited_to_user(self):
        new_user = create_user(
            email='newuser@example.com',
            password='newuserpass123',
        )
        Ingredient.objects.create(user=new_user, name='Pepper')

        Ingredient.objects.create(user=self.user, name='Salt')
        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.filter(
            user=self.user
        ).order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_ingredient(self):
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )
        url = detail_url(ingredient_id=ingredient_salt.id)

        payload = {
            'name': 'Pepper',
        }

        res = self.client.patch(url, payload)
        ingredient_salt.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload['name'], ingredient_salt.name)

    def test_delete_ingredient(self):
        ingredient_pepper = Ingredient.objects.create(
            user=self.user,
            name='Pepper',
        )
        url = detail_url(ingredient_id=ingredient_pepper.id)

        res = self.client.delete(url)

        ingredients = Ingredient.objects.filter(
            user=self.user,
        ).order_by('-name')

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        ing1 = Ingredient.objects.create(
            user=self.user,
            name='Sugar',
        )
        ing2 = Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )

        recipe = Recipe.objects.create(
            user=self.user,
            title='Chocolate Cake',
            time_minutes=5,
            price=Decimal('7.5'),
        )
        recipe.ingredients.add(ing1)

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)

        params = {'assigned_only': 1}
        res = self.client.get(INGREDIENTS_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_unique_ingredients_assigned_to_recipes(self):
        ing = Ingredient.objects.create(
            user=self.user,
            name='Sugar',
        )
        Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )

        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Chocolate Cake',
            time_minutes=10,
            price=Decimal('12'),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Vanilla Cake',
            time_minutes=8,
            price=Decimal('9'),
        )

        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        params = {'assigned_only': 1}
        res = self.client.get(INGREDIENTS_URL, params)
        self.assertEqual(len(res.data), 1)
