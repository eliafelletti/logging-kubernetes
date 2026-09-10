## 📄 Abstract
This project presents a robust, scalable, and fully observable Cloud-Native architecture built for a Flask-based microservice. Evolving from a baseline academic prototype, the system has been entirely re-engineered to feature a High-Availability PostgreSQL database tier, dynamic horizontal autoscaling, controlled chaos engineering, and a comprehensive telemetry stack deployed on Kubernetes.

---

## 🚀 Key Features Highlights
* **High Availability & Autoscaling:** Dynamic load management using the Horizontal Pod Autoscaler (HPA) and a resilient PostgreSQL HA cluster with Pgpool-II for read/write splitting and failover.
* **Advanced Observability & Alerting:** Full-stack telemetry leveraging Prometheus, Loki, and Grafana to bridge the gap between application-level API requests and underlying database interactions, coupled with automated alerting rules.
* **Resilience & Chaos Engineering:** Built-in fault injection mechanisms to test system boundaries, paired with rigorous stress testing via Locust to ensure stability and graceful degradation under high concurrent loads.

---

## 🛠️ Tech Stack
* **Backend:** Python 3.11 / Flask, SQLAlchemy (ORM)
* **Database Tier:** PostgreSQL HA, Pgpool-II
* **Infrastructure:** Kubernetes (Minikube), Docker, NGINX Ingress
* **Observability Suite:** Grafana, Prometheus, Loki, Promtail, Alertmanager
* **Query Languages:** PromQL, LogQL
* **Testing & QA:** Pytest, Hypothesis (PBT), Playwright (E2E), Locust (Load Testing)
* **CI/CD:** GitHub Actions

---

## 📂 Repository Structure

The project repository is strictly organized to separate the application source code, infrastructure deployment manifests, automated testing suites, and architectural documentation. *(Note: Local development caches and virtual environments are excluded from version control).*

```text
.
├── .github/workflows/      # CI/CD Pipeline definitions (GitHub Actions)
├── app/                    # Backend application context
│   ├── src/                # Application source code (Flask API, SQLAlchemy ORM)
│   ├── tests/              # Automated test suite (Unit, PBT, E2E)
│   ├── .env.example        # Environment variables template
│   ├── Dockerfile          # Container configuration for the Flask microservice
│   └── requirements.txt    # Python dependencies
├── docs/                   # Architectural specifications and presentation slides (PDFs)
├── k8s/                    # Kubernetes manifests
│   ├── app/                # Application manifests (Deployment, HPA, Ingress)
│   ├── database/           # PostgreSQL HA and Pgpool-II configurations
│   └── monitoring/         # Grafana dashboard JSON
├── scripts/                # Operational scripts
│   └── locustfile.py       # Locust load testing scenarios
├── .gitignore              # Git ignored files and directories
├── pytest.ini              # Pytest configuration settings
└── README.md               # Main project documentation

```

---

## 🚀 Quickstart

### Prerequisites
* Docker Engine & Minikube
* `kubectl` and `helm` CLI
* Python 3.11+

### 1. Cluster Initialization & Namespaces
Start the local cluster, enable the required addons, and isolate the environment by creating dedicated namespaces:

```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress metrics-server

kubectl create namespace app
kubectl create namespace database
kubectl create namespace monitoring
```

### 2. Database Deployment (PostgreSQL HA)
Create the required credentials for PostgreSQL and Pgpool-II, then deploy the High Availability cluster inside the `database` namespace:

```bash
# Generate DB and Replication Secrets
kubectl create secret generic pg-secret -n database \
  --from-literal=password="supersecretpassword" \
  --from-literal=repmgr-password="repmgrpassword"

# Generate Pgpool-II Admin Secrets
kubectl create secret generic pgpool-secret -n database \
  --from-literal=admin-password="adminpgpoolpassword" \
  --from-literal=sr-check-password="healthcheckpassword"

# Deploy via Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install postgresql-ha bitnami/postgresql-ha -n database
```
(Wait for the database pods to be fully initialized and running before proceeding).

---

### 3. Application Deployment
Create the Flask application credentials and apply the Kubernetes manifests (Deployment, Services, Ingress, and HPA) in the `app` namespace:

```bash
# Generate Application Secrets
kubectl create secret generic flask-app-secret -n app \
  --from-literal=db-password="supersecretpassword" \
  --from-literal=secret-key="development-key-1234567890"

# Apply Application Manifests and HPA
kubectl apply -k k8s/app/ -n app
```
(Wait for the application pods to be fully initialized and running before proceeding).

---

### 4. Observability Stack (Prometheus & Loki)
Deploy the monitoring and logging components into the `monitoring` namespace. We disable Loki's bundled Grafana to rely on the Prometheus stack's instance.

```bash
# Release Prometheus Stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# Release Loki Stack (without bundled Grafana)
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack -n monitoring --set grafana.enabled=false
```
(Wait for the monitoring pods to be fully initialized and running before proceeding).

**⚠️ Important Data Source Configuration:**  
To prevent Loki from overriding Prometheus as the default data source in Grafana, you must patch its ConfigMap:
```bash
kubectl edit configmap loki-loki-stack -n monitoring
```
Locate the `isDefault` flag under the datasources section, change it from `true` to `false`, then save and exit.

---

### 5. Accessing Services & Grafana Dashboard
You can access the services either via the Minikube IP (`minikube ip`) using the `/etc/hosts` DNS configuration, or directly via `port-forward`:

```bash
# Example port-forwarding for the Application and Grafana
kubectl port-forward svc/flask-app-service 8080:80 -n app
kubectl port-forward svc/prometheus-grafana 8081:80 -n monitoring
```
#### Grafana setup:
1. Extract the auto-generated `admin` password:
   ```bash
   kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
   ```
2. Log into Grafana (`http://localhost:8081` or `http://grafana.local`), and change the password immediately upon first login.
3. Import the system dashboard by navigating to Dashboards -> Import -> Upload JSON file and selecting the `k8s/monitoring/grafana_dashboard.json` file provided in this repository.

---

### 6. Load Testing & Autoscaling (Locust)
To verify the system's resilience and observe the Horizontal Pod Autoscaler (HPA) in action, you can simulate concurrent traffic using the provided Locust script.

#### Locust setup:
1. Start the Locust load testing tool from the root of the repository:
   ```bash
   locust -f scripts/locustfile.py
   ```
2. Open the Locust Web UI in your browser at `http://localhost:8089`.
3. Configure the load parameters (e.g., Number of users: `20`, Spawn rate: `0.2`) and click Start.
4. Navigate back to your Grafana Dashboard to watch the panels "animate" with real-time metrics, logs, and traffic spikes.
