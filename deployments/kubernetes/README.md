# Kubernetes manifests

Plain manifests for self-hosted GovAI Core. **Not** a multi-replica HA ledger — default `replicas: 1` with a ReadWriteOnce ledger volume.

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
# cp secret.example.yaml secret.yaml && edit && kubectl apply -f secret.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Or use the Helm chart under `deployments/helm/govai-core/`.
