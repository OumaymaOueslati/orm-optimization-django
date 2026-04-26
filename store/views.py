import time
from django.shortcuts import render
from django.db import connection, reset_queries
from django.db.models import Sum, Count, F
from .models import Order


def orders_slow(request):
    reset_queries()
    start_time = time.time()

    # ❌ VERSION LENTE — problème N+1
    orders = list(Order.objects.all()[:100]) ## 1 requête pour les 100 commandes

    for order in orders:  #On parcourt chaque commande une par une
        # ← requête SQL pour chaque client
        order.customer_name = order.customer.name  # ← 1 requête SQL par commande = 100 requêtes
        order.customer_city = order.customer.city

        # ← requête SQL pour chaque commande
        items = order.items.all()  #Django va chercher les produits de la commande dans la table OrderItem, ce qui génère une requête SQL par commande (100 requêtes supplémentaires)
        order.nb_items = len(items) #on compte combien de produits dans la commande

        # ← requête SQL pour chaque produit
        total = 0
        for item in items:
            total += item.unit_price * item.quantity
        order.computed_total = round(total, 2)

    end_time = time.time()
    execution_time = round((end_time - start_time) * 1000, 2) #Calcul du temps d'exécution en millisecondes
    query_count = len(connection.queries) #combien de requêtes SQL ont été exécutées

    print(f"\n🐌 LENTE — {query_count} requêtes — {execution_time} ms\n")

    return render(request, 'store/orders_slow.html', { #envoie les données à la page HTML pour affichage
        'orders': orders,
        'query_count': query_count,
        'execution_time': execution_time,
    })


def orders_fast(request):
    reset_queries()
    start_time = time.time()

    # ✅ VERSION RAPIDE — optimisée
    orders = list(
        Order.objects
        .select_related('customer') 
        .prefetch_related('items__product')
        .annotate(
            nb_items=Count('items'), #compter combien d’items (produits) dans une commande
            computed_total=Sum(F('items__unit_price') * F('items__quantity')) #F() “prends la valeur de la colonne dans la base”
        )[:100] #limite à 100 commandes pour éviter de surcharger la mémoire et le temps de traitement
    )

    end_time = time.time()
    execution_time = round((end_time - start_time) * 1000, 2)
    query_count = len(connection.queries)

    print(f"\n⚡ RAPIDE — {query_count} requêtes — {execution_time} ms\n")

    return render(request, 'store/orders_fast.html', {
        'orders': orders,
        'query_count': query_count,
        'execution_time': execution_time,
    })