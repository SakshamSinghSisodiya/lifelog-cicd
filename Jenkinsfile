pipeline {
    agent any

    environment {
        DOCKERHUB_USER = 'saksham122004'
        BACKEND_IMAGE  = "${DOCKERHUB_USER}/lifelog-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/lifelog-frontend"
        APP_VERSION    = '1.0.0'
    }

    triggers {
        // Fallback if the GitHub webhook is not configured: check for commits every 5 minutes
        pollSCM('H/5 * * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                echo "Building ${DOCKERHUB_USER}/lifelog-* :${BUILD_NUMBER} from commit ${env.GIT_SHORT}"
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements.txt
                    pytest -q
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    for part in backend frontend; do
                        docker build -f ${part}/Dockerfile \
                            --build-arg APP_VERSION=${APP_VERSION} \
                            --build-arg GIT_COMMIT=${GIT_SHORT} \
                            --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                            -t ${DOCKERHUB_USER}/lifelog-${part}:${BUILD_NUMBER} \
                            -t ${DOCKERHUB_USER}/lifelog-${part}:latest .
                    done
                '''
            }
        }

        stage('Push Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_TOKEN')]) {
                    // Single-quoted so Groovy never interpolates the secret into the log
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        for part in backend frontend; do
                            docker push ${DOCKERHUB_USER}/lifelog-${part}:${BUILD_NUMBER}
                            docker push ${DOCKERHUB_USER}/lifelog-${part}:latest
                        done
                    '''
                }
            }
        }

        stage('Deploy to Minikube') {
            steps {
                sh '''
                    sed -i "s|image: .*|image: ${BACKEND_IMAGE}:${BUILD_NUMBER}|" k8s/backend.yaml
                    sed -i "s|image: .*|image: ${FRONTEND_IMAGE}:${BUILD_NUMBER}|" k8s/frontend.yaml
                    kubectl apply -f k8s/
                    kubectl rollout status deployment/lifelog-backend --timeout=120s
                    kubectl rollout status deployment/lifelog-frontend --timeout=120s
                '''
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    kubectl get pods,deploy,svc
                    MINIKUBE_IP=$(minikube ip)
                    echo "Checking http://${MINIKUBE_IP}:30080/health"
                    for i in 1 2 3 4 5 6; do
                        CODE=$(curl -s -o /tmp/health.json -w "%{http_code}" http://${MINIKUBE_IP}:30080/health || true)
                        [ "$CODE" = "200" ] && break
                        echo "Attempt $i: got $CODE, retrying..."; sleep 5
                    done
                    cat /tmp/health.json; echo
                    [ "$CODE" = "200" ] || { echo "Health check failed"; exit 1; }
                '''
            }
        }
    }

    post {
        always {
            sh 'docker logout || true'
        }
        failure {
            sh '''
                kubectl describe deployment/lifelog-backend deployment/lifelog-frontend || true
                kubectl get pods || true
                kubectl logs deploy/lifelog-backend --tail=50 || true
                kubectl logs deploy/lifelog-frontend --tail=50 || true
            '''
        }
    }
}
