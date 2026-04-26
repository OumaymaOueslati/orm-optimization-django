import os
import django
import time
import threading

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_project.settings')
django.setup()

from django.db import connection, reset_queries, transaction
from store.models import Order


# ============================================================
# SCENARIO 1 — SANS atomic (dangereux)
# ============================================================

def scenario_sans_atomic():
    print("\n" + "="*60)
    print("SCENARIO 1 — SANS transaction.atomic()")
    print("Probleme : race condition possible !")
    print("="*60)

    errors = []
    results = []
    lock = threading.Lock()

    def worker_sans_atomic(thread_id):
        try:
            order = Order.objects.first()
            time.sleep(0.005)
            old_status = order.status
            with lock:
                results.append({
                    'thread': thread_id,
                    'status_lu': old_status,
                })
        except Exception as e:
            with lock:
                errors.append(f"Thread {thread_id}: {str(e)}")

    threads = [
        threading.Thread(target=worker_sans_atomic, args=(i,))
        for i in range(10)
    ]

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = round((time.time() - start) * 1000, 2)

    print(f"\nThreads lances    : 10")
    print(f"Threads reussis   : {len(results)}/10")
    print(f"Erreurs           : {len(errors)}")
    print(f"Temps total       : {duration} ms")
    print(f"\nRisque : {len(results)} threads ont lu la meme")
    print(f"donnee en meme temps sans protection !")
    print(f"→ Resultat potentiellement incoherent ❌")


# ============================================================
# SCENARIO 2 — AVEC atomic (correct)
# ============================================================

def scenario_avec_atomic():
    print("\n" + "="*60)
    print("SCENARIO 2 — AVEC transaction.atomic()")
    print("Solution : les threads attendent leur tour !")
    print("="*60)

    errors = []
    times = []
    lock = threading.Lock()

    def worker_avec_atomic(thread_id):
        try:
            start = time.time()
            with transaction.atomic():
                order = Order.objects.select_for_update().first()
                time.sleep(0.01)
                duration = round((time.time() - start) * 1000, 2)
                with lock:
                    times.append(duration)
                    print(f"  Thread {thread_id:02d} → "
                          f"status={order.status} | "
                          f"temps={duration}ms ✅")
        except Exception as e:
            with lock:
                errors.append(f"Thread {thread_id}: {str(e)}")
                print(f"  Thread {thread_id:02d} → ERREUR: {e} ❌")

    threads = [
        threading.Thread(target=worker_avec_atomic, args=(i,))
        for i in range(10)
    ]

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = round((time.time() - start) * 1000, 2)

    print(f"\nThreads lances    : 10")
    print(f"Threads reussis   : {len(times)}/10")
    print(f"Erreurs de lock   : {len(errors)}")
    print(f"Temps total       : {total} ms")
    print(f"Temps moyen       : {round(sum(times)/len(times), 2)} ms")
    print(f"Temps max         : {max(times)} ms")
    print(f"Temps min         : {min(times)} ms")
    print(f"→ Resultat coherent garanti ✅")


# ============================================================
# SCENARIO 3 — ROLLBACK automatique
# ============================================================

def scenario_rollback():
    print("\n" + "="*60)
    print("SCENARIO 3 — ROLLBACK automatique")
    print("Si erreur → tout est annule automatiquement !")
    print("="*60)

    order = Order.objects.first()
    status_avant = order.status
    print(f"\nStatut AVANT : {status_avant}")

    try:
        with transaction.atomic():
            order.status = 'confirmed'
            order.save()
            print(f"Statut PENDANT transaction : {order.status}")
            raise Exception("Erreur simulee — rollback !")

    except Exception as e:
        print(f"Erreur interceptee : {e}")

    order.refresh_from_db()
    print(f"Statut APRES rollback : {order.status}")

    if order.status == status_avant:
        print("→ Rollback reussi ! Donnees inchangees ✅")
    else:
        print("→ PROBLEME : donnees modifiees malgre erreur ❌")


# ============================================================
# SCENARIO 4 — Nested atomic (savepoints)
# ============================================================

def scenario_nested_atomic():
    print("\n" + "="*60)
    print("SCENARIO 4 — Nested atomic (Savepoints)")
    print("atomic() dans atomic() = savepoint PostgreSQL")
    print("="*60)

    order = Order.objects.first()
    status_original = order.status
    print(f"\nStatut original : {status_original}")

    try:
        with transaction.atomic():
            order.status = 'confirmed'
            order.save()
            print(f"Transaction principale : status = {order.status}")

            try:
                with transaction.atomic():
                    order.status = 'shipped'
                    order.save()
                    print(f"Savepoint : status = {order.status}")
                    raise Exception("Erreur dans le savepoint !")

            except Exception as e:
                print(f"Savepoint annule : {e}")
                order.refresh_from_db()
                print(f"Apres annulation savepoint : {order.status}")

            print(f"Transaction principale continue : {order.status}")

        order.refresh_from_db()
        print(f"Statut final apres commit : {order.status}")
        print("→ Savepoint annule, transaction principale commitee ✅")

    finally:
        order.status = status_original
        order.save()


# ============================================================
# SCENARIO 5 — DEADLOCK
# ============================================================

def scenario_deadlock():
    print("\n" + "="*60)
    print("SCENARIO 5 — DEADLOCK")
    print("Thread A attend Thread B et Thread B attend Thread A !")
    print("="*60)

    orders = list(Order.objects.all()[:2])
    if len(orders) < 2:
        print("Pas assez de commandes pour le test !")
        return

    order1_id = orders[0].id
    order2_id = orders[1].id

    results = []
    lock = threading.Lock()

    def thread_A():
        try:
            with transaction.atomic():
                o1 = Order.objects.select_for_update(
                    nowait=True
                ).get(id=order1_id)
                print(f"  Thread A → verrouille Order #{order1_id} ✅")
                time.sleep(0.5)

                print(f"  Thread A → essaie Order #{order2_id}...")
                o2 = Order.objects.select_for_update(
                    nowait=True
                ).get(id=order2_id)
                print(f"  Thread A → verrouille Order #{order2_id} ✅")

                with lock:
                    results.append("Thread A : SUCCESS")

        except Exception as e:
            with lock:
                results.append(f"Thread A : BLOQUE → {type(e).__name__}")
                print(f"  Thread A → BLOQUE ❌ ({type(e).__name__})")

    def thread_B():
        try:
            time.sleep(0.1)
            with transaction.atomic():
                o2 = Order.objects.select_for_update(
                    nowait=True
                ).get(id=order2_id)
                print(f"  Thread B → verrouille Order #{order2_id} ✅")
                time.sleep(0.5)

                print(f"  Thread B → essaie Order #{order1_id}...")
                o1 = Order.objects.select_for_update(
                    nowait=True
                ).get(id=order1_id)
                print(f"  Thread B → verrouille Order #{order1_id} ✅")

                with lock:
                    results.append("Thread B : SUCCESS")

        except Exception as e:
            with lock:
                results.append(f"Thread B : BLOQUE → {type(e).__name__}")
                print(f"  Thread B → BLOQUE ❌ ({type(e).__name__})")

    print("\nSimulation deadlock avec nowait=True :")
    print("(nowait=True → echoue immediatement si verrou pris)")
    print()

    t1 = threading.Thread(target=thread_A)
    t2 = threading.Thread(target=thread_B)

    start = time.time()
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    duration = round((time.time() - start) * 1000, 2)

    print(f"\nResultats :")
    for r in results:
        print(f"  → {r}")
    print(f"\nTemps total : {duration} ms")
    print("""
Comment eviter le deadlock :
  ✅ Toujours verrouiller dans le meme ordre
  ✅ Utiliser nowait=True pour detecter rapidement
  ✅ Utiliser select_for_update(skip_locked=True)
  ✅ Reduire la duree des transactions
    """)
    print("="*60)


# ============================================================
# RESUME FINAL
# ============================================================

def resume():
    print("\n" + "="*60)
    print("RESUME — Comportement des atomic blocks")
    print("="*60)
    print("""
┌─────────────────────┬────────────────────────────────────┐
│ Concept             │ Comportement                       │
├─────────────────────┼────────────────────────────────────┤
│ Sans atomic         │ Race condition possible ❌          │
│ Avec atomic         │ Threads attendent leur tour ✅      │
│ select_for_update   │ Verrou au niveau ligne ✅           │
│ Rollback            │ Erreur → tout annule auto ✅        │
│ Nested atomic       │ Savepoint → rollback partiel ✅     │
│ Deadlock (nowait)   │ Detecte et echoue rapidement ✅     │
└─────────────────────┴────────────────────────────────────┘
    """)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("DEMONSTRATION COMPLETE — Atomic Blocks")
    print("Comportement sous transactions paralleles")
    print("="*60)

    scenario_sans_atomic()
    scenario_avec_atomic()
    scenario_rollback()
    scenario_nested_atomic()
    scenario_deadlock()
    resume()

    print("\nDemonstration atomic blocks terminee ! ✅")