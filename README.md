# LifeLog: CI/CD with Jenkins, Docker, Docker Hub and Minikube

## 1. Project chosen

**LifeLog** is a small personal life tracker (Python 3.12, Flask, SQLite, gunicorn).
Version 1 has three modules:

- **Habits**: add habits, daily check-in toggle, current and longest streak.
- **Expenses**: log amount, category and date; monthly total per category; monthly budget with percent used.
- **Dashboard**: today's habits, this month's spend vs budget, streak highlights.

The footer of every page shows the version, build number, git commit and pod name, so a pipeline run is visible in the browser.
The UI uses an "origami fold" look (paper cards with folded corners, creases and layered shadows) in a single CSS file.

Run locally:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
flask --app wsgi run        # http://127.0.0.1:5000
```

Layout: `app/` (factory, routes, `db.py`, pure logic in `habits_logic.py` and `expenses_logic.py`), `tests/`, `Dockerfile`, `Jenkinsfile`, `k8s/`.

## 2. Pipeline stages

| Stage | What it does |
|---|---|
| Checkout | Jenkins clones the GitHub repo and records the short commit id. |
| Build & Test | Creates a Python venv, installs `requirements.txt`, runs `pytest`. A failing test stops the pipeline. |
| Docker Build | Builds `saksham122004/lifelog` with build args `APP_VERSION`, `GIT_COMMIT`, `BUILD_NUMBER`; tags `:<build number>` and `:latest`. |
| Push Image | Logs in to Docker Hub with credential `dockerhub-creds` (`--password-stdin`) and pushes both tags. |
| Deploy to Minikube | Writes the new image tag into `k8s/deployment.yaml`, runs `kubectl apply -f k8s/`, waits with `kubectl rollout status`. |
| Verify | Lists pods/deployments/services, then curls `http://$(minikube ip):30080/health` and fails the build unless it returns 200. |

`post { always }` runs `docker logout`; `post { failure }` prints `kubectl describe` and pod logs.
A `pollSCM` trigger checks GitHub every 5 minutes as a fallback when no webhook exists.

## 3. How Jenkins was set up on AWS

1. EC2 Ubuntu 22.04, t3.medium, 30 GB disk. Security group: 22 (my IP), 8080 (Jenkins), 30080 (app).
2. Installed Docker, Java 17, Jenkins, kubectl, Minikube (docker driver) and git.
3. Added the `jenkins` user to the `docker` group and started Minikube as `jenkins`, so pipeline `kubectl` and `minikube` commands work.
4. Unlocked Jenkins at `http://<ec2-ip>:8080`, installed suggested plugins plus Docker Pipeline and Pipeline Stage View, created an admin user.
5. Added Docker Hub access token as credential `dockerhub-creds` (Username with password).
6. Created Pipeline job "lifelog-pipeline": Pipeline script from SCM, Git, this repo, branch `main`, path `Jenkinsfile`.

## 4. How the image was pushed

The pipeline builds the image on the EC2 host and pushes `saksham122004/lifelog:<build>` and `:latest` to Docker Hub.
An access token is used instead of the account password: it can be revoked, scoped, and never exposes the real password.

## 5. How it was deployed and accessed

`k8s/deployment.yaml` runs 2 replicas with readiness and liveness probes on `/health`, small resource limits, and the pod name injected through the downward API.
`k8s/service.yaml` is a NodePort service on 30080 (port 80 to container port 5000).

Minikube with the docker driver runs inside a Docker network on the EC2 host, so `<ec2-public-ip>:30080` does not reach it directly.
Pipeline checks use `minikube ip` from inside EC2. For the browser, forward the service on all interfaces:

```bash
sudo -u jenkins kubectl port-forward --address 0.0.0.0 svc/lifelog 30080:80
```

Then open `http://<ec2-public-ip>:30080`.

## 6. What changed for the second run

Branch `v2-goals` adds a **Goals** module (name, target, progress, deadline, percent complete) with its own tests.
Merging it into `main` and pushing triggers a new build. The footer build number changes, the pod name changes after the rolling update, and a Goals link appears in the navigation.
The Jenkinsfile version also moves from 1.0.0 to 2.0.0.

Persistence note: SQLite lives inside each pod, so data resets when a pod is replaced and each replica has its own data. A PersistentVolumeClaim (or a shared database) would fix this; it is left out to keep the assignment focused on the pipeline.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied` on `/var/run/docker.sock` | `sudo usermod -aG docker jenkins` then `sudo systemctl restart jenkins`. |
| `minikube: host does not exist` / `kubectl` cannot connect in a build | Minikube is not running for the jenkins user: `sudo -u jenkins minikube start --driver=docker`. |
| `ImagePullBackOff` | Wrong Docker Hub username or the push failed; check the Push Image log and that the repo is public. |
| `Verify` stage gets no 200 | `kubectl get pods`, then `kubectl logs deploy/lifelog`; wait for readiness. |
| Port 30080 not reachable from the browser | Open the port in the security group and run the `port-forward` command above. |
| `python3 -m venv` fails | `sudo apt install -y python3-venv`. |
| Pipeline did not start on push | No webhook: wait for pollSCM (5 min) or click Build Now. |

## 8. Screenshots

See `docs/report.pdf` for labelled screenshot slots.
