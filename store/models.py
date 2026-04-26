from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True) #L'email doit être unique pour éviter les doublons
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True) #Enregistre automatiquement la date et l'heure de création du client

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['category'], name='idx_product_category'),
        ]


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]
    customer = models.ForeignKey(  #Un client peut avoir plusieurs commandes, mais une commande appartient à un seul client. C'est une relation de type "ForeignKey" (clé étrangère) dans Django.
        Customer,
        on_delete=models.CASCADE, #Si un client est supprimé, toutes ses commandes seront également supprimées (cascade delete).
        related_name='orders' #Permet d'accéder aux commandes d'un client via l'attribut "orders" (ex: customer.orders.all())
    )
    status = models.CharField( 
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return f"Order #{self.id}"

    class Meta:
        indexes = [
            models.Index(
                fields=['-created_at', 'status'], #- created_at signifie ordre décroissant 
                name='idx_order_created_status'
            ),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(  #Une commande peut avoir plusieurs items, mais un item appartient à une seule commande. C'est une relation de type "ForeignKey" (clé étrangère) dans Django.
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey( 
        Product,
        on_delete=models.CASCADE, 
        related_name='order_items'
    )
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"