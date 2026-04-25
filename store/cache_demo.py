import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_project.settings')
django.setup()

from django.core.cache import cache
from django.db import reset_queries, connection
from django.db.models import Sum, Count, F
from store.models import Order

CACHE_KEY = 'orders_list'
CACHE_TIMEOUT = 60  # secondes


def get_orders_with_cache():
    """
    Vérifie d'abord le cache avant de toucher la base de données.
    Si les données sont en cache → retourne directement (0 requête SQL)
    Sinon → fait la requête et met en cache
    """
    reset_queries()
    start = time.time()

    # Essaie de récupérer depuis le cache
    orders = cache.get(CACHE_KEY)

    if orders is None:
        print("CACHE MISS — requête vers la base de données...")

        # Pas en cache → requête optimisée
        orders = list(
            Order.objects
            .select_related('customer')
            .annotate(
                nb_items=Count('items'),
                computed_total=Sum(F('items__unit_price') * F('items__quantity'))
            )[:100]
        )

        # Stocke en cache
        cache.set(CACHE_KEY, orders, CACHE_TIMEOUT)
        source = "BASE DE DONNÉES"
    else:
        print("CACHE HIT — données récupérées depuis le cache !")
        source = "CACHE"

    duration = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    print(f"Source           : {source}")
    print(f"Requêtes SQL     : {query_count}")
    print(f"Temps            : {duration} ms")
    print(f"Nb commandes     : {len(orders)}")
    return orders


def demo_denormalization():
    """
    Montre le concept de dénormalisation :
    Ajouter un champ total_price calculé directement dans Order
    pour éviter de recalculer à chaque requête
    """
    print("\n" + "="*60)
    print("DÉMONSTRATION DÉNORMALISATION")
    print("="*60)
    print("""
    Concept : Au lieu de calculer le total à chaque requête :
    
    SANS dénormalisation (coûteux) :
    → SELECT SUM(unit_price * quantity) FROM store_orderitem
      WHERE order_id = X
    → Exécuté pour CHAQUE commande affichée
    
    AVEC dénormalisation (rapide) :
    → Champ total_price stocké directement dans store_order
    → Mis à jour via signal Django post_save sur OrderItem
    → SELECT total_price FROM store_order → 1 seule requête !
    
    LIMITE : Si un OrderItem est modifié par 2 utilisateurs
    simultanément, le total_price peut devenir incohérent.
    Solution : transaction.atomic() + select_for_update()
    """)


if __name__ == "__main__":
    print("="*60)
    print("TEST CACHE — Django Cache Framework (mémoire locale)")
    print("="*60)

    print("\n--- Appel 1 (premier appel) ---")
    get_orders_with_cache()

    print("\n--- Appel 2 (depuis le cache) ---")
    get_orders_with_cache()

    print("\n--- Invalidation du cache ---")
    cache.delete(CACHE_KEY)
    print("Cache supprimé !")

    print("\n--- Appel 3 (après invalidation) ---")
    get_orders_with_cache()

    demo_denormalization()