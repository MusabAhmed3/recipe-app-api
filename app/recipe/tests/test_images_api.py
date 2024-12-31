import tempfile
import os

from decimal import Decimal
from PIL import Image

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Recipe


def create_image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


class PrivateImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='testuser@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='test recipe',
            time_minutes=4,
            price=Decimal('3.30'),
        )

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_recipe_image_file(self):
        url = create_image_upload_url(recipe_id=self.recipe.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file_name:
            img = Image.new('RGB', (10, 10))
            img.save(image_file_name, format='JPEG')
            image_file_name.seek(0)
            payload = {'image': image_file_name}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_recipe_image_file_bad_request(self):
        url = create_image_upload_url(recipe_id=self.recipe.id)

        payload = {'image': 'hithere'}

        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
