from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        email = 'test@example.com'
        password = 'password123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        sample_emails = [
            ['test@EXAMPLE.COM', 'test@example.com'],
            ['Test@Example.com', 'Test@example.com'],
            ['TEST@example.COM', 'TEST@example.com'],
            ['tesT@EXAMPLE.com', 'tesT@example.com']
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(
                email,
                'testpass123'
            )
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                '',
                'testpass123'
            )

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'testpass123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe_success(self):
        user = get_user_model().objects.create(
            name='Test User',
            email='test@example.com',
            password='passtest123',
            )
        recipe = models.Recipe.objects.create(
            user=user,
            title='Test Recipe',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample Recipe Description',
            link='http://example.com/sample-recipe.pdf',
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        user = get_user_model().objects.create_user(
            email='user@example.com',
            password='pass123user'
        )
        tag = models.Tag.objects.create(user=user, name='Fruity')

        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        user = get_user_model().objects.create_user(
            email='user@example.com',
            password='passuser123',
        )
        ingredient = models.Ingredient.objects.create(user=user, name='Salt')

        self.assertEqual(str(ingredient), ingredient.name)

    @patch('core.models.uuid.uuid4')
    def test_generate_recipe_image_file_path(self, mock_uuid):
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        image_file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(image_file_path, f'uploads/recipe/{uuid}.jpg')
