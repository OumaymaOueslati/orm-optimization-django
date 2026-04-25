import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker
from store.models import Customer, Product, Order, OrderItem

fake = Faker('fr_FR')

class Command(BaseCommand):
    help = 'Génère des données de test'

    def handle(self, *args, **kwargs):
        self.stdout.write('Génération des données...')

        # 500 clients
        customers = []
        for _ in range(500):
            customers.append(Customer(
                name=fake.name(),
                email=fake.unique.email(),
                city=fake.city(),
            ))
        Customer.objects.bulk_create(customers)
        self.stdout.write('500 clients créés')

        # 100 produits
        categories = ['Electronics', 'Clothing', 'Food', 'Books', 'Sports']
        products = []
        for _ in range(100):
            products.append(Product(
                name=fake.word().capitalize() + ' ' + fake.word(),
                price=Decimal(str(round(random.uniform(5, 500), 2))),
                stock=random.randint(0, 1000),
                category=random.choice(categories),
            ))
        Product.objects.bulk_create(products)
        self.stdout.write('100 produits créés')

        # 2000 commandes
        all_customers = list(Customer.objects.all())
        all_products = list(Product.objects.all())
        statuses = ['pending', 'confirmed', 'shipped', 'delivered']

        for _ in range(2000):
            order = Order.objects.create(
                customer=random.choice(all_customers),
                status=random.choice(statuses),
            )
            for _ in range(random.randint(1, 5)):
                product = random.choice(all_products)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 10),
                    unit_price=product.price,
                )

        self.stdout.write(self.style.SUCCESS('Base de données remplie avec succès !'))