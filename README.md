# Long-Running HTTP Test with Envoy and Azure APIM Gateway

This project demonstrates how to use Envoy and a backend delay app (`http_waiter.py`) to support long-running (30+ min) HTTP requests, even when the client does not send keep-alives. It includes Azure API Management self-hosted gateway integration for cloud deployments.

## Local Development

### How to Run Locally

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

## Deploying to Azure Kubernetes Service (AKS)

## 🎯 Key Findings & Configuration

### Architecture Overview
The complete traffic flow is: **Client → Envoy Proxy → Azure APIM Self-hosted Gateway → http-waiter**

### Critical Configuration Requirements

#### 1. Azure APIM Backend Configuration
**⚠️ IMPORTANT**: The backend service URL in Azure APIM must be configured as **HTTP** (not HTTPS):
```
Backend URL: http://http-waiter:8080
```

#### 2. API Operation Setup
In your Azure APIM instance, you MUST explicitly define operations. The gateway will return 404 for undefined operations.

**Required API Operation Configuration:**
- **HTTP Method**: `GET`
- **URL Template**: `/delay`
- **Backend**: Routes to `http://http-waiter:8080/delay`

#### 3. Query Parameters
Add the following query parameter to the `/delay` operation:
- **Name**: `timeout`
- **Type**: `integer`
- **Required**: `false`
- **Description**: `Delay duration in seconds`

### 🔧 Step-by-Step APIM Configuration

1. **Navigate to Azure Portal** → API Management → `your-apim-instance`

2. **Configure Backend Service:**
   - Go to **APIs** → Select your API (or create new)
   - Navigate to **Settings** tab
   - Set **Web service URL** to: `http://http-waiter:8080`
   - ⚠️ **Critical**: Use `http://` NOT `https://`

3. **Add the Delay Operation:**
   - Click **+ Add operation**
   - **Display name**: `Delay Test`
   - **Name**: `delay`
   - **HTTP verb**: `GET`
   - **URL template**: `/delay`

4. **Add Query Parameters:**
   - Go to **Query** tab in the operation
   - Add parameter: `timeout` (integer, optional)

5. **Assign to Gateway:**
   - Go to **Gateways** → Your gateway name
   - Ensure your API is assigned in the **APIs** tab

### 🧪 Testing Commands

```powershell
# Start port forwarding to Envoy
kubectl port-forward service/envoy 8080:8080

# Test short delay (30 seconds)
Invoke-WebRequest -Uri "http://localhost:8080/delay?timeout=30" -Method GET

# Test medium delay (5 minutes)
Invoke-WebRequest -Uri "http://localhost:8080/delay?timeout=300" -Method GET

# Test long delay (20 minutes)
Invoke-WebRequest -Uri "http://localhost:8080/delay?timeout=1200" -Method GET
```

### 📊 Expected Behavior
- **Response Time**: Matches the `timeout` parameter
- **HTTP Status**: 200 OK
- **Connection**: Maintained throughout the delay period
- **Logs**: Progress updates every second in http-waiter logs

### Prerequisites

- Azure CLI installed and configured
- kubectl installed
- Docker installed
- Access to an AKS cluster
- Azure Container Registry (ACR) or other container registry
- Azure API Management instance (for APIM gateway)

### Step 1: Prepare Your Container Images

#### Build and Push the HTTP Waiter Image

```powershell
# Build your custom application image
docker build -t your-registry.azurecr.io/http-waiter:latest .

# Login to your Azure Container Registry
az acr login --name your-registry

# Push the image
docker push your-registry.azurecr.io/http-waiter:latest
```

#### Update the Kubernetes Manifest

Edit `k8s-deployment.yaml` and update the image reference:

```yaml
# Change this line in the http-waiter deployment:
# FROM: image: acrhhdemo.azurecr.io/http-waiter:latest
# TO:   image: your-registry.azurecr.io/http-waiter:latest
```

### Step 2: Configure Azure APIM Self-Hosted Gateway

#### Get Gateway Configuration from Azure Portal

1. Navigate to your Azure API Management instance in the Azure Portal
2. Go to **Gateways** > **Self-hosted**
3. Create a new gateway or select an existing one
4. Copy the **Gateway Key** and **Configuration endpoint**

#### Required Placeholder Replacements

Before deploying, you must update these values in `k8s-deployment.yaml`:

| Location | Current Placeholder | Replace With |
|----------|-------------------|--------------|
| `laptopgateway-env` ConfigMap | `config.service.endpoint: "apim-hh-demo1.configuration.azure-api.net"` | `config.service.endpoint: "your-apim-instance.configuration.azure-api.net"` |
| `laptopgateway` deployment | `config.service.auth` value: `""` | Your actual gateway key from Azure Portal |
| `http-waiter` deployment | `image: acrhhdemo.azurecr.io/http-waiter:latest` | `image: your-registry.azurecr.io/http-waiter:latest` |

#### Update the Kubernetes Manifest

Edit `k8s-deployment.yaml` and replace the placeholder values:

```yaml
# In the laptopgateway-env ConfigMap, replace:
config.service.endpoint: "your-apim-instance.configuration.azure-api.net"

# In the laptopgateway deployment, replace the empty auth value:
- name: config.service.auth
  value: "your-actual-gateway-key-here"
```

**⚠️ Security Note:** For production deployments, use Kubernetes secrets instead of plain text values:

```yaml
# Create a secret first:
kubectl create secret generic apim-gateway-secret --from-literal=gateway-key="your-actual-gateway-key-here"

# Then reference it in the deployment:
- name: config.service.auth
  valueFrom:
    secretKeyRef:
      name: apim-gateway-secret
      key: gateway-key
```

### Step 3: Connect to Your AKS Cluster

```powershell
# Get AKS credentials
az aks get-credentials --resource-group your-resource-group --name your-aks-cluster

# Verify connection
kubectl get nodes
```

### Step 4: Deploy to AKS

#### Pre-Deployment Validation

Before deploying, verify all placeholder values have been replaced:

```powershell
# Check that all placeholders are updated
grep -n "acrhhdemo.azurecr.io\|apim-hh-demo1\|\"\"" k8s-deployment.yaml

# If this command returns results, you still have placeholders to replace
```

**Expected Configuration Check:**
- ✅ Container image should reference your registry (not `acrhhdemo.azurecr.io`)
- ✅ APIM endpoint should reference your instance (not `apim-hh-demo1`)
- ✅ Gateway auth should have a value (not empty `""`)

#### Deploy All Resources

```powershell
# Apply the Kubernetes manifest
kubectl apply -f k8s-deployment.yaml

# Verify deployments
kubectl get deployments
kubectl get services
kubectl get pods
```

#### Check Pod Status

```powershell
# Monitor pod startup
kubectl get pods -w

# Check logs if needed
kubectl logs deployment/http-waiter
kubectl logs deployment/envoy
kubectl logs deployment/apim-gateway
```

### Step 5: Expose Services (Optional)

#### Option A: LoadBalancer Service (Recommended for testing)

Create a LoadBalancer service to expose Envoy:

```yaml
# Save as envoy-loadbalancer.yaml
apiVersion: v1
kind: Service
metadata:
  name: envoy-loadbalancer
spec:
  type: LoadBalancer
  selector:
    app: envoy
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
```

Apply it:
```powershell
kubectl apply -f envoy-loadbalancer.yaml
kubectl get service envoy-loadbalancer
```

#### Option B: Ingress Controller

If you have an ingress controller configured:

```yaml
# Save as ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
spec:
  rules:
    - host: your-app.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: envoy
                port:
                  number: 8080
```

### Step 6: Testing Your Deployment

#### Test Internal Connectivity

```powershell
# Port forward to test locally
kubectl port-forward service/envoy 8080:8080

# In another terminal, test the endpoint
curl http://localhost:8080
```

#### Test via LoadBalancer (if configured)

```powershell
# Get external IP
kubectl get service envoy-loadbalancer

# Test with external IP
curl http://EXTERNAL-IP
```

#### Test APIM Gateway

```powershell
# Port forward APIM gateway
kubectl port-forward service/apim-gateway 8081:8080

# Test APIM gateway health
curl http://localhost:8081/health
```

### Step 7: Monitoring and Troubleshooting

#### Check Pod Logs

```powershell
# View logs for each component
kubectl logs -l app=http-waiter
kubectl logs -l app=envoy
kubectl logs -l app=apim-gateway

# Follow logs in real-time
kubectl logs -f deployment/envoy
```

#### Debug Pod Issues

```powershell
# Describe pods for events
kubectl describe pod -l app=http-waiter

# Get into a pod for debugging
kubectl exec -it deployment/envoy -- /bin/bash
```

#### Check Service Connectivity

```powershell
# Test internal service resolution
kubectl run test-pod --image=busybox -it --rm -- nslookup http-waiter
kubectl run test-pod --image=busybox -it --rm -- wget -qO- http://http-waiter:8080
```

### Step 8: Scaling and Production Considerations

#### Scale Deployments

```powershell
# Scale http-waiter replicas
kubectl scale deployment http-waiter --replicas=3

# Scale envoy replicas
kubectl scale deployment envoy --replicas=2
```

#### Add Resource Limits (Recommended for Production)

Edit `k8s-deployment.yaml` to add resource requests and limits:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

#### Configure Health Checks

Add liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Clean Up

To remove all deployed resources:

```powershell
kubectl delete -f k8s-deployment.yaml
kubectl delete service envoy-loadbalancer  # if created
```

## Architecture Overview

```
Internet → LoadBalancer → Envoy Proxy → HTTP Waiter
                     ↓
              APIM Self-Hosted Gateway
```

- **HTTP Waiter**: Your custom application
- **Envoy Proxy**: Load balancer and proxy with long-running request support (30-minute timeouts)
- **APIM Gateway**: Azure API Management self-hosted gateway for API management

## What This Shows

- Envoy is configured to allow idle and request timeouts up to 30 minutes.
- The backend app simulates a long-running request and logs progress.
- The test client does not use keep-alives, verifying true long-lived connections.
- Azure APIM self-hosted gateway provides enterprise API management capabilities.

## Troubleshooting Common Issues

### 1. **404 "OperationNotFound" Error**
**Symptom**: Gateway logs show: `"reason":"OperationNotFound","message":"Unable to match incoming request to an operation"`

**Solution**: 
- Verify the API operation is defined in Azure APIM
- Check that the URL template matches exactly (e.g., `/delay`)
- Ensure the API is assigned to your gateway

### 2. **Backend Connection Errors**
**Symptom**: Gateway cannot reach the backend service

**Solutions**:
- ✅ Use `http://http-waiter:8080` (HTTP, not HTTPS)
- ✅ Verify service names match in Kubernetes
- ✅ Check that all pods are running: `kubectl get pods`

### 3. **APIM Gateway Authentication Issues**
**Symptom**: Gateway fails to connect to Azure APIM, logs show authentication errors

**Solutions**:
- ✅ Verify the `config.service.auth` value is set (not empty `""`)
- ✅ Ensure you're using the correct gateway key from Azure Portal
- ✅ Check the `config.service.endpoint` uses `.configuration.azure-api.net` (not `.management.`)
- ✅ Verify the gateway is properly registered in Azure Portal

**Check Configuration**:
```powershell
# Verify the gateway configuration
kubectl get configmap laptopgateway-env -o yaml

# Check if auth value is set (should not be empty)
kubectl get deployment laptopgateway -o yaml | grep -A 5 "config.service.auth"
```

### 4. **Port Forwarding Issues**
**Symptom**: Cannot connect to `localhost:8080`

**Solutions**:
```powershell
# Stop existing port-forwards
kubectl port-forward --help

# Restart port-forward
kubectl port-forward service/envoy 8080:8080
```

### 5. **Long Request Timeouts**
**Symptom**: Requests timeout before completion

**Solution**: Envoy is configured for 30-minute timeouts (1800s). For longer requests, modify the `envoy.yaml` configuration.

### 6. **Image Pull Errors**
**Solution**: 
```powershell
# Ensure ACR is attached to AKS
az aks update -n your-aks-cluster -g your-resource-group --attach-acr your-acr-name
```

### 🔍 Debugging Commands

```powershell
# Check pod status
kubectl get pods -o wide

# View logs
kubectl logs deployment/envoy
kubectl logs deployment/laptopgateway
kubectl logs deployment/http-waiter

# Test internal connectivity
kubectl run test-pod --image=busybox -it --rm -- wget -qO- http://http-waiter:8080

# Check service endpoints
kubectl get endpoints
```

For more detailed troubleshooting, check the pod logs and events using the commands above.