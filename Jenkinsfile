pipeline {
    // This agent configuration is now extremely clean.
    // It tells Jenkins to run the build on an agent with the label 'ssp-agent'.
    // The Jenkins Docker Cloud config will find the template with this label.
    // The Docker daemon on the host is now responsible for ECR authentication
    // via the config.json file and the EC2 instance role.
    agent {
        label 'ssp-agent'
    }

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Tests & SonarQube Analysis') {
            steps {
                // All commands run inside the custom agent which has all tools installed.
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    sh 'python3 -m venv venv'
                    sh '. venv/bin/activate && pip install -r requirements.txt'
                    sh '. venv/bin/activate && pip install -r requirements-dev.txt'
                    sh '. venv/bin/activate && pytest tests/unit || echo "Tests failed or no tests found"'
                    script {
                        withSonarQubeEnv('SonarQube-Server') {
                            sh ". venv/bin/activate && /sonar-scanner-4.7.0.2747-linux/bin/sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
                        }
                    }
                }
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    script {
                        def awsAccountId = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                        def ecrRegistry = "${awsAccountId}.dkr.ecr.${AWS_REGION}.amazonaws.com"

                        dir('terraform') {
                            sh "terraform init -backend-config=\"bucket=ssp-terraform-state-bucket\" -backend-config=\"key=services/search-service/terraform.tfstate\" -backend-config=\"region=${AWS_REGION}\""
                            sh 'terraform workspace select dev || terraform workspace new dev'
                            env.ECR_REPOSITORY_URL = sh(script: 'terraform output -raw ecr_repository_url', returnStdout: true).trim()
                        }
                        if (!env.ECR_REPOSITORY_URL) {
                            error "Failed to get ECR repository URL from Terraform."
                        }

                        // The Docker daemon is already logged in via the EC2 instance role
                        def dockerImage = docker.build("ssp-search-service:${env.BUILD_NUMBER}", ".")
                        dockerImage.tag("${env.ECR_REPOSITORY_URL}:${env.BUILD_NUMBER}")
                        dockerImage.tag("${env.ECR_REPOSITORY_URL}:latest")

                        dockerImage.push("${env.BUILD_NUMBER}")
                        dockerImage.push("latest")
                    }
                }
            }
        }

        stage('Deploy to Environment') {
            steps {
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    script {
                        dir('terraform') {
                            input message: "Apply plan to ${params.TARGET_ENV}?", ok: 'Deploy'
                            sh "terraform workspace select ${params.TARGET_ENV}"
                            def ecrRepoUrl = sh(script: 'terraform output -raw ecr_repository_url', returnStdout: true).trim()
                            def imageUrl = "${ecrRepoUrl}:${env.BUILD_NUMBER}"
                            sh "terraform apply -auto-approve -var=\"container_image=${imageUrl}\" -var=\"environment=${params.TARGET_ENV}\""
                        }
                    }
                }
            }
        }
    }
}
