from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order


class OrderRedirectTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='order-customer',
            password='test-password',
        )
        self.order = Order.objects.create(
            user=self.user,
            delivery_fee=0,
            total_amount=25,
            is_paid=True,
        )

    def test_payment_success_url_redirects_to_order_history(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('order_success'))

        self.assertRedirects(response, reverse('order_history'))

    def test_order_history_shows_paid_orders_after_redirect(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('order_success'), follow=True)

        self.assertEqual(response.redirect_chain[-1][0], reverse('order_history'))
        self.assertContains(response, f'Order #{self.order.id}')
