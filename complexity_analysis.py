import os
import django
import time
import threading
import tracemalloc

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_project.settings')
django.setup()

from django.db import connection, reset_queries
from django.db.models import Sum, Count, F
from store.models import Order


def analyze_slow():
    """Analyse version lente — N+1"""
    tracemalloc.start()
    reset_queries()
    start = time.time()

    orders = list(Order.objects.all()[:100])
    for order in orders:
        order.customer_name = order.customer.name
        order.customer_city = order.customer.city
        items = order.items.all()
        order.nb_items = len(items)
        total = 0
        for item in items:
            total += item.unit_price * item.quantity
        order.computed_total = round(total, 2)

    duration = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n" + "="*60)
    print("VERSION LENTE — Analyse complète")
    print("="*60)
    print(f"Nombre de requêtes SQL : {query_count}")
    print(f"Temps d'exécution      : {duration} ms")
    print(f"Mémoire utilisée       : {round(current/1024, 2)} KB")
    print(f"Mémoire peak           : {round(peak/1024, 2)} KB")
    print("\nDétail des 5 premières requêtes SQL :")
    for i, q in enumerate(connection.queries[:5]):
        print(f"  [{i+1}] {q['time']}s → {q['sql'][:80]}...")
    print("="*60)

    return query_count, duration, peak


def analyze_fast():
    """Analyse version rapide — optimisée"""
    tracemalloc.start()
    reset_queries()
    start = time.time()

    orders = list(
        Order.objects
        .select_related('customer')
        .prefetch_related('items__product')
        .annotate(
            nb_items=Count('items'),
            computed_total=Sum(F('items__unit_price') * F('items__quantity'))
        )[:100]
    )

    duration = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n" + "="*60)
    print("VERSION RAPIDE — Analyse complète")
    print("="*60)
    print(f"Nombre de requêtes SQL : {query_count}")
    print(f"Temps d'exécution      : {duration} ms")
    print(f"Mémoire utilisée       : {round(current/1024, 2)} KB")
    print(f"Mémoire peak           : {round(peak/1024, 2)} KB")
    print("\nDétail des requêtes SQL :")
    for i, q in enumerate(connection.queries):
        print(f"  [{i+1}] {q['time']}s → {q['sql'][:80]}...")
    print("="*60)

    return query_count, duration, peak


def analyze_lock_contention():
    """Test de lock contention avec transactions parallèles"""
    print("\n" + "="*60)
    print("ANALYSE LOCK CONTENTION — 10 threads parallèles")
    print("="*60)

    errors = []
    times = []
    lock = threading.Lock()

    def worker(thread_id):
        from django.db import transaction
        start = time.time()
        try:
            with transaction.atomic():
                # Simule une lecture avec lock
                order = Order.objects.select_for_update().first()
                time.sleep(0.01)  # simule un traitement
                duration = round((time.time() - start) * 1000, 2)
                with lock:
                    times.append(duration)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"Threads réussis  : {len(times)}/10")
    print(f"Erreurs de lock  : {len(errors)}")
    print(f"Temps moyen      : {round(sum(times)/len(times), 2)} ms")
    print(f"Temps max        : {max(times)} ms")
    print(f"Temps min        : {min(times)} ms")
    if errors:
        print(f"Erreurs          : {errors}")
    print("="*60)


def compare():
    """Tableau comparatif final"""
    print("\n" + "="*60)
    print("TABLEAU COMPARATIF FINAL")
    print("="*60)

    sq, st, sp = analyze_slow()
    fq, ft, fp = analyze_fast()

    print("\n")
    print(f"{'Métrique':<25} {'LENTE':>15} {'RAPIDE':>15} {'Gain':>10}")
    print("-"*65)
    print(f"{'Requêtes SQL':<25} {sq:>15} {fq:>15} {round(sq/fq)}{'x':>9}")
    print(f"{'Temps (ms)':<25} {st:>15} {ft:>15} {round(st/ft)}{'x':>9}")
    print(f"{'Mémoire peak (KB)':<25} {round(sp/1024,2):>15} {round(fp/1024,2):>15}")
    print("="*60)

    analyze_lock_contention()


if __name__ == "__main__":
    compare()