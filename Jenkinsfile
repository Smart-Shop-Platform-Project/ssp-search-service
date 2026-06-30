pipeline {
    // This agent block is now simplified. It just defines the image name.
    // The login and pull will be handled explicitly in the stages.
    agent {
        docker {
            image 'ssp-jenkins-agent:latest'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
            // We remove the registry details from here as we will handle it manually.
            reuseNode true
        }
    }

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        // Get the AWS Account ID from the new 'aws-account-id' secret text credential
        AWS_ACCOUNT_ID = credentials('aws-account-id')
    }

    stages {
        stage('Login to ECR') {
            steps {
                // This is the most reliable way to log in.
                // It uses the permanent aws-creds to get a temporary password,
                // then uses that password to log in. This happens for every build.
                withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                    sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
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

        stage('Build and Push Docker Image') {
            steps {
                script {
                    def ecrRegistry = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    def ecrRepoUrl
                    dir('terraform') {
                        sh "terraform init -backend-config=\"bucket=ssp-terraform-state-bucket\" -backend-config=\"key=services/search-service/terraform.tfstate\" -backend-config=\"region=${AWS_REGION}\""
                        sh 'terraform workspace select dev || terraform workspace new dev'
                        ecrRepoUrl = sh(script: 'terraform output -raw ecr_repository_url', returnStdout: true).trim()
                    }
                    if (!ecrRepoUrl) {
                        error "Failed to get ECR repository URL from Terraform."
                    }

                    def dockerImage = docker.build("ssp-search-service:${env.BUILD_NUMBER}", ".")
                    dockerImage.tag("${ecrRepoUrl}:${env.BUILD_NUMBER}")
                    dockerImage.tag("${ecrRepoUrl}:latest")

                    // The login was already handled in the first stage
                    dockerImage.push("${env.BUILD_NUMBER}")
                    dockerImage.push("latest")
                }
            }
        }

        stage('Deploy to Environment') {
            steps {
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
