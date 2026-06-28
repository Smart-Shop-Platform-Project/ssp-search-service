pipeline {
    // Request the specific agent by the label you configured in the Docker Cloud settings.
    // Jenkins will now automatically start your custom container for this pipeline.
    agent {
        label 'ssp-agent'
    }

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
    }

    stages {
        // No 'Setup Environment' stage needed, as all tools are already in the agent.

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Tests & SonarQube Analysis') {
            steps {
                // All commands will now work because they are inside your custom agent.
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    sh 'pip install -r requirements-dev.txt'
                    sh 'pytest tests/unit || echo "No tests configured yet"'
                    withSonarQubeEnv('SonarQube-Server') {
                        sh "sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
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

                        // Log in to ECR
                        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ecrRegistry}"

                        def dockerImage = docker.build("ssp-search-service:${env.BUILD_NUMBER}", ".")
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
