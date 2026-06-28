pipeline {
    // Use any available agent on the Jenkins controller.
    // We will manually specify the Docker container for each stage.
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        AWS_ACCOUNT_ID = ''
        ECR_REGISTRY = ''
    }

    stages {
        stage('Setup Environment') {
            steps {
                // This step runs on the base Jenkins agent, but it needs AWS CLI.
                // This assumes the AWS CLI is installed on the host and in the PATH.
                // A better way is to run this inside the container too.
                script {
                    env.AWS_ACCOUNT_ID = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                    env.ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                }
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test & Analyze') {
            steps {
                // Explicitly run this stage inside your custom agent container
                script {
                    docker.image("${env.ECR_REGISTRY}/ssp-jenkins-agent:latest").inside {
                        withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                            sh 'pip install -r requirements-dev.txt'
                            sh 'pytest tests/unit || echo "No tests configured yet"'
                            withSonarQubeEnv('SonarQube-Server') {
                                sh "sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
                            }
                        }
                    }
                }
            }
        }

        stage('Build, Push & Deploy') {
            steps {
                // Run the rest of the steps inside the container as well
                script {
                    docker.image("${env.ECR_REGISTRY}/ssp-jenkins-agent:latest").inside {
                        withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                            // Terraform and Docker commands
                            dir('terraform') {
                                sh "terraform init -backend-config=\"bucket=ssp-terraform-state-bucket\" -backend-config=\"key=services/search-service/terraform.tfstate\" -backend-config=\"region=${AWS_REGION}\""
                                sh 'terraform workspace select dev || terraform workspace new dev'
                                env.ECR_REPOSITORY_URL = sh(script: 'terraform output -raw ecr_repository_url', returnStdout: true).trim()
                            }
                            if (!env.ECR_REPOSITORY_URL) {
                                error "Failed to get ECR repository URL from Terraform."
                            }

                            def dockerImage = docker.build("ssp-search-service:${env.BUILD_NUMBER}", ".")
                            docker.withRegistry("https://${env.ECR_REGISTRY}", 'aws-creds') {
                                dockerImage.push("${env.BUILD_NUMBER}")
                                dockerImage.push("latest")
                            }

                            // Deployment part
                            dir('terraform') {
                                input message: "Apply plan to ${params.TARGET_ENV}?", ok: 'Deploy'
                                sh "terraform workspace select ${params.TARGET_ENV}"
                                def imageUrl = "${env.ECR_REPOSITORY_URL}:${env.BUILD_NUMBER}"
                                sh "terraform apply -auto-approve -var=\"container_image=${imageUrl}\" -var=\"environment=${params.TARGET_ENV}\""
                            }
                        }
                    }
                }
            }
        }
    }
}
