import requests
import time

def check_api(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()

        response_time = end_time - start_time

        if response.status_code != 200:
            health = "DOWN"
        else:
            if response_time > 2:
                health = "DEGRADED"
            else:
                health = "HEALTHY"

        return {
            "url": url,
            "status_code": response.status_code,
            "response_time": round(response_time, 3),
            "health": health
        }

    except:
        return {
            "url": url,
            "status_code": 0,
            "response_time": 999,
            "health": "DOWN"
        }