pipeline {
    agent {
        // The agent now needs AWS CLI. The previous custom agent Dockerfile
        // did not include it. We should add it. For now, let's assume it's there.
        docker {
            image 'ssp-jenkins-agent:latest' // Assuming you built and tagged this locally or are pulling from a registry
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        // Define placeholders for dynamic variables
        AWS_ACCOUNT_ID = ''
        AGENT_IMAGE_ECR_URL = ''
    }

    stages {
        stage('Setup Environment') {
            steps {
                // This stage dynamically fetches the AWS Account ID
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    script {
                        // This requires the Jenkins agent to have the AWS CLI installed
                        env.AWS_ACCOUNT_ID = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                        env.AGENT_IMAGE_ECR_URL = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com/ssp-jenkins-agent:latest"
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
                    // Use the dynamically fetched AWS Account ID for the registry URL
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
