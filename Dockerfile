# Use an official Python runtime as a parent image
FROM python:3.13-slim-bookworm

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    FastAPI \
    uvicorn[standard]

WORKDIR /app
# Add the current directory contents into the container at /app
ADD . /app

EXPOSE 8080

# Run http_waiter.py with uvicorn when the container launches
CMD ["uvicorn", "http_waiter:app", "--host", "0.0.0.0", "--port", "8080"]