import threading
import urllib.request
import time

SLOW_URL = "http://127.0.0.1:8000/store/orders-slow/"
FAST_URL = "http://127.0.0.1:8000/store/orders-fast/"

results = []
lock = threading.Lock()

def fetch(url, label):
    start = time.time()
    try:
        urllib.request.urlopen(url)
        duration = round((time.time() - start) * 1000, 2)
        with lock:
            results.append((label, duration, "OK"))
    except Exception as e:
        with lock:
            results.append((label, 0, f"ERREUR: {e}"))

def run_test(url, label, nb_threads=20):
    print(f"\n{'='*50}")
    print(f"Test : {label} avec {nb_threads} utilisateurs simultanés")
    print('='*50)
    results.clear()

    threads = [threading.Thread(target=fetch, args=(url, label)) 
               for _ in range(nb_threads)]
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = round((time.time() - start) * 1000, 2)

    times = [r[1] for r in results if r[2] == "OK"]
    print(f"Temps total      : {total} ms")
    print(f"Temps moyen      : {round(sum(times)/len(times), 2)} ms")
    print(f"Temps max        : {max(times)} ms")
    print(f"Temps min        : {min(times)} ms")
    print(f"Requêtes réussies: {len(times)}/{nb_threads}")

if __name__ == "__main__":
    print("Assure-toi que le serveur Django tourne !")
    print("Lance : python manage.py runserver\n")
    
    run_test(SLOW_URL, "VERSION LENTE", nb_threads=20)
    time.sleep(2)
    run_test(FAST_URL, "VERSION RAPIDE", nb_threads=20)