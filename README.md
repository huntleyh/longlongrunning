# Long-Running HTTP Test with Envoy and http_waiter

This project demonstrates how to use Envoy and a backend delay app (`http_waiter.py`) to support long-running (30+ min) HTTP requests, even when the client does not send keep-alives.

## How to Run

1. **Start the stack:**
   ```bash
   docker-compose up
   ```

2. **Test a long-running request:**
   ```bash
   curl -v \
     --http1.1 \
     --no-buffer \
     --no-keepalive \
     --header "Connection: close" \
     --max-time 1800 \
     --connect-timeout 10 \
     http://localhost:8080/delay?timeout=1200
   ```

3. **Observe backend logs:**

   Example output from the backend app:
   ```
   http-waiter-1  | 2025-08-01 00:30:59,111 [INFO] wait-loop: 1197/1200s elapsed, connection healthy=True
   http-waiter-1  | 2025-08-01 00:31:00,112 [INFO] wait-loop: 1198/1200s elapsed, connection healthy=True
   http-waiter-1  | 2025-08-01 00:31:01,113 [INFO] wait-loop: 1199/1200s elapsed, connection healthy=True
   http-waiter-1  | 2025-08-01 00:31:02,113 [INFO] Finished /delay for 172.19.0.3: intended=1200s, actual=1200s
   http-waiter-1  | INFO:     172.19.0.3:59870 - "GET /delay?timeout=1200 HTTP/1.1" 200 OK
   ```

## What This Shows

- Envoy is configured to allow idle and request timeouts up to 30 minutes.
- The backend app simulates a long-running request and logs progress.
- The test client does not use keep-alives, verifying true long-lived