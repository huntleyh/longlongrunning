import asyncio
import logging
import socket
from datetime import datetime

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

@app.get("/")
async def read_root():
    server_name = socket.gethostname()
    return {"Hello": "World from " + server_name}


@app.get("/delay")
async def delay_response(request: Request, timeout: int = Query(0, description="Time to delay the response in seconds")):
    """
    Endpoint that delays the response based on the timeout parameter,
    but logs each second that the wait-loop is still running, and
    checks TCP connection health via request.is_disconnected().
    """
    client_ip = request.client.host
    server_name = socket.gethostname()
    logger.info(f"New /delay request from {client_ip} (host {server_name}), delay={timeout}s")

    # Attempt to log underlying socket keep-alive setting
    try:
        transport = request.scope.get("transport")
        sock = transport.get_extra_info("socket") if transport else None
        if sock:
            ka = sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
            logger.info(f"Underlying TCP socket fileno={sock.fileno()}, SO_KEEPALIVE={ka}")
        else:
            logger.warning("Could not retrieve raw socket from ASGI transport")
    except Exception as e:
        logger.exception("Error inspecting TCP socket for keep-alive")

    start_time = datetime.utcnow()
    elapsed = 0

    # run a 1-second loop rather than a single sleep, so we can log progress
    while elapsed < timeout:
        # log the wait-loop status
        logger.info(f"wait-loop: {elapsed}/{timeout}s elapsed, connection healthy={not await request.is_disconnected()}")
        await asyncio.sleep(1)
        elapsed += 1

        # if client disconnected, bail out early
        if await request.is_disconnected():
            logger.warning(f"Client {client_ip} disconnected after {elapsed}s; stopping delay")
            break

    end_time = datetime.utcnow()
    logger.info(f"Finished /delay for {client_ip}: intended={timeout}s, actual={elapsed}s")

    response = {
        "timeout": timeout,
        "start": start_time.isoformat() + "Z",
        "end":   end_time.isoformat() + "Z",
        "actual_delay": elapsed,
        "client_disconnected": await request.is_disconnected()
    }

    return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting app with Uvicorn (HTTP/1.1 only)")
    uvicorn.run(app, host="0.0.0.0", port=8080)
