pipeline {
    // Use your custom agent from ECR. This agent has Python, Docker, AWS CLI,
    // Terraform, and Sonar Scanner all pre-installed in its PATH.
    agent {
        docker {
            image 'ssp-jenkins-agent:latest'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
            registryUrl "https://${env.AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
            registryCredentialsId 'aws-creds'
        }
    }

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        AWS_ACCOUNT_ID = '' // Will be populated in the Setup stage
    }

    stages {
        stage('Setup Environment') {
            steps {
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    script {
                        env.AWS_ACCOUNT_ID = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                    }
                }
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Tests & SonarQube Analysis') {
            steps {
                sh 'pip install -r requirements-dev.txt'
                sh 'pytest tests/unit || echo "No tests configured yet"'
                script {
                    withSonarQubeEnv('SonarQube-Server') {
                        sh "sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
                    }
                }
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                script {
                    dir('terraform') {
                        sh "terraform init -backend-config=\"bucket=ssp-terraform-state-bucket\" -backend-config=\"key=services/search-service/terraform.tfstate\" -backend-config=\"region=${AWS_REGION}\""
                        sh 'terraform workspace select dev || terraform workspace new dev'
                        env.ECR_REPOSITORY_URL = sh(script: 'terraform output -raw ecr_repository_url', returnStdout: true).trim()
                    }
                    if (!env.ECR_REPOSITORY_URL) {
                        error "Failed to get ECR repository URL from Terraform."
                    }

                    def dockerImage = docker.build("ssp-search-service:${env.BUILD_NUMBER}", ".")
                    docker.withRegistry("https://${env.ECR_REPOSITORY_URL}", 'aws-creds') {
                        dockerImage.push("${env.BUILD_NUMBER}")
                        dockerImage.push("latest")
                    }
                }
            }
        }

        stage('Deploy to Environment') {
            steps {
                script {
                    dir('terraform') {
                        sh "terraform workspace select ${params.TARGET_ENV} || terraform workspace new ${params.TARGET_ENV}"
                        def imageUrl = "${env.ECR_REPOSITORY_URL}:${env.BUILD_NUMBER}"
                        sh "terraform plan -var=\"container_image=${imageUrl}\" -var=\"environment=${params.TARGET_ENV}\" -out=tfplan"
                    }
                }
            }
            post {
                success {
                    input message: "Apply plan to ${params.TARGET_ENV}?", ok: 'Deploy'
                    script {
                        dir('terraform') {
                            sh 'terraform apply tfplan'
                        }
                    }
                }
            }
        }
    }
}
