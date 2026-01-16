import requests
import time
import concurrent.futures
import sys

# Configuration - HEAVY LOAD TEST
NUM_BATCHES = 5             # Number of batches to fire
REQUESTS_PER_BATCH = 500    # Increased from 100 to 500
BATCH_INTERVAL = 5          # Seconds between batches
MAX_WORKERS = 100           # Max concurrent connections

def send_request(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        latency = time.time() - start_time
        return response.status_code, latency
    except Exception as e:
        return f"ERROR: {type(e).__name__}", 0.0

def load_test(url):
    print(f"🔥🔥🔥 HEAVY LOAD TEST 🔥🔥🔥")
    print(f"🚀 Target: {url}")
    print(f"🎯 Config: {REQUESTS_PER_BATCH} requests x {NUM_BATCHES} batches")
    print(f"📊 Total Expected: {REQUESTS_PER_BATCH * NUM_BATCHES} requests")
    print(f"⚙️ Max Concurrent Workers: {MAX_WORKERS}")
    print("=" * 60)
    
    total_requests = 0
    success_count = 0
    error_count = 0
    all_latencies = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for batch_num in range(NUM_BATCHES):
            batch_start = time.time()
            print(f"🔥 Batch {batch_num + 1}/{NUM_BATCHES}: Firing {REQUESTS_PER_BATCH} requests...")
            
            futures = [executor.submit(send_request, url) for _ in range(REQUESTS_PER_BATCH)]
            
            batch_success = 0
            batch_error = 0
            for future in concurrent.futures.as_completed(futures):
                status, latency = future.result()
                total_requests += 1
                if status == 200:
                    success_count += 1
                    batch_success += 1
                    all_latencies.append(latency)
                else:
                    error_count += 1
                    batch_error += 1
            
            elapsed = time.time() - batch_start
            success_rate = 100 * batch_success / REQUESTS_PER_BATCH
            print(f"   ✅ {batch_success}/{REQUESTS_PER_BATCH} ({success_rate:.0f}%) | ⏱️ {elapsed:.1f}s")
            
            # Wait for next batch
            if batch_num < NUM_BATCHES - 1:
                sleep_time = max(0, BATCH_INTERVAL - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print(f"📊 Total Requests: {total_requests}")
    success_pct = 100*success_count/total_requests if total_requests > 0 else 0
    print(f"✅ Success: {success_count} ({success_pct:.1f}%)")
    print(f"❌ Errors: {error_count}")
    if all_latencies:
        avg_latency = sum(all_latencies) / len(all_latencies)
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
        p95 = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        print(f"⏱️ Latency:")
        print(f"   avg={avg_latency*1000:.0f}ms | min={min_latency*1000:.0f}ms | max={max_latency*1000:.0f}ms | p95={p95*1000:.0f}ms")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 load_test.py <URL>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    load_test(target_url)
