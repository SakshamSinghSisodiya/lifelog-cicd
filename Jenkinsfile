pipeline {
    agent any

    environment {
        DOCKERHUB_USER = 'saksham122004'
        IMAGE          = "${DOCKERHUB_USER}/lifelog"
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
                echo "Building ${IMAGE}:${BUILD_NUMBER} from commit ${env.GIT_SHORT}"
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
                    docker build \
                        --build-arg APP_VERSION=${APP_VERSION} \
                        --build-arg GIT_COMMIT=${GIT_SHORT} \
                        --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                        -t ${IMAGE}:${BUILD_NUMBER} \
                        -t ${IMAGE}:latest .
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
                        docker push ${IMAGE}:${BUILD_NUMBER}
                        docker push ${IMAGE}:latest
                    '''
                }
            }
        }

        stage('Deploy to Minikube') {
            steps {
                sh '''
                    sed -i "s|image: .*|image: ${IMAGE}:${BUILD_NUMBER}|" k8s/deployment.yaml
                    kubectl apply -f k8s/
                    kubectl rollout status deployment/lifelog --timeout=120s
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
                kubectl describe deployment/lifelog || true
                kubectl get pods -l app=lifelog || true
                kubectl logs -l app=lifelog --tail=50 || true
            '''
        }
    }
}
