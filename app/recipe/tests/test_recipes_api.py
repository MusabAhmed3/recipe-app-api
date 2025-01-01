from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample Test Recipe',
        'time_minutes': 5,
        'price': Decimal('5.50'),
        'description': 'Sample Test Recipe Description',
        'link': 'http://www.example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


class PublicRecipeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_list_recipes_unauthorized(self):
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='passtest123',
            name='Test User',
        )
        self.client.force_authenticate(self.user)

    def test_get_recipes_authorized_user(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipes_belong_authorized_user(self):
        other_user = get_user_model().objects.create_user(
            email='otheruser@example.com',
            password='otherpass123',
            name='Other User',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 5,
            'price': Decimal('5.50'),
            'description': 'Sample Test Recipe Description',
            'link': 'http://www.example.com/recipe.pdf',
        }
        res = self.client.post(RECIPES_URL, payload)
        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipe.user, self.user)
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

    def test_partial_update(self):
        original_url = 'http://www.example.com/new_url'
        recipe = create_recipe(
            user=self.user,
            title='Sample Test Recipe',
            description='Sample Test Recipe Description',
            link=original_url,
        )

        payload = {'title': 'New Sample Title'}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_url)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(user=self.user)

        payload = {
            'title': 'New Test Recipe',
            'time_minutes': 7,
            'price': Decimal('7.50'),
            'description': 'New Sample Test Recipe Description',
            'link': 'http://www.example.com/new_recipe.pdf',
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.user, self.user)
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

    def test_update_user_error(self):
        new_user = get_user_model().objects.create_user(
            email='newuser@example.com',
            password='newpass1234',
        )
        payload = {'user': new_user.id}

        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_user_recipe_error(self):
        new_user = get_user_model().objects.create_user(
            email='newuser@example.com',
            password='newpass1234',
        )

        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_tags(self):
        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 7,
            'price': Decimal('3.50'),
            'tags': [
                {'name': 'Fruity'},
                {'name': 'Dinner'},
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                user=self.user,
                name=tag['name']
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 7,
            'price': Decimal('3.50'),
            'tags': [
                {'name': 'Breakfast'},
                {'name': 'Dessert'},
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_breakfast, recipe.tags.all())

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                user=self.user,
                name=tag['name']
            ).exists()
            self.assertTrue(exists)

    def test_update_recipe_with_new_tag(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe_id=recipe.id)

        payload = {
            'tags': [
                {'name': 'Dinner'},
            ]
        }
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tag_dinner = Tag.objects.get(user=self.user, name='Dinner')
        self.assertIn(tag_dinner, recipe.tags.all())

    def test_update_recipe_assign_existing_tag(self):
        tag_fruity = Tag.objects.create(user=self.user, name='Fruity')

        recipe = create_recipe(user=self.user)
        url = detail_url(recipe_id=recipe.id)

        payload = {
            'tags': [
                {'name': 'Fruity'},
            ]
        }

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_fruity, recipe.tags.all())

    def test_create_recipe_with_new_ingredients(self):
        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 3,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': 'Salt'},
                {'name': 'Pepper'},
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name'],
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )

        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 3,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': 'Salt'},
                {'name': 'Pepper'},
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_salt, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(exists)

    def test_update_recipe_with_new_tags(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe_id=recipe.id)

        payload = {
            'ingredients': [
                {'name': 'Salt'},
                {'name': 'SUgar'},
            ]
        }

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name'],
            ).exists()
            self.assertTrue(exists)

    def test_update_recipe_with_existing_tags(self):
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe_id=recipe.id)

        payload = {
            'ingredients': [
                {'name': 'Salt'},
                {'name': 'Pepper'},
            ]
        }

        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_salt, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name'],
            ).exists()
            self.assertTrue(exists)

    def test_update_recipe_clear_tags(self):
        ingredient_salt = Ingredient.objects.create(
            user=self.user,
            name='Salt',
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_salt)

        url = detail_url(recipe_id=recipe.id)

        payload = {
            'ingredients': []
        }

        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_recipes_by_tags(self):
        r1 = create_recipe(user=self.user, title='Chicken Kofte')
        r2 = create_recipe(user=self.user, title='Biryani')
        r3 = create_recipe(user=self.user, title='Aloo Matter')

        t1 = Tag.objects.create(user=self.user, name='Spicy')
        t2 = Tag.objects.create(user=self.user, name='Masala dar')

        r1.tags.add(t1)
        r2.tags.add(t2)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        params = {'tags': f'{t1.id},{t2.id}'}
        res = self.client.get(RECIPES_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        r1 = create_recipe(user=self.user, title='Chicken Kofte')
        r2 = create_recipe(user=self.user, title='Biryani')
        r3 = create_recipe(user=self.user, title='Aloo Matter')

        i1 = Ingredient.objects.create(user=self.user, name='Chicken Masala')
        i2 = Ingredient.objects.create(user=self.user, name='Biryani Masala')

        r1.ingredients.add(i1)
        r2.ingredients.add(i2)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        params = {'ingredients': f'{i1.id},{i2.id}'}
        res = self.client.get(RECIPES_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)
