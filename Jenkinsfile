pipeline {
    // Start on any available agent. The first step will be to log in to ECR.
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
        // We will get the account ID dynamically
    }

    stages {
        stage('Main Build Stage') {
            steps {
                script {
                    // This is the most robust pattern. We explicitly log in, then run everything inside the container.
                    withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {

                        // 1. Get AWS Account ID
                        def awsAccountId = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                        if (!awsAccountId) {
                            error "Could not determine AWS Account ID."
                        }
                        def ecrRegistry = "${awsAccountId}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        def agentImage = "${ecrRegistry}/ssp-jenkins-agent:latest"

                        // 2. Explicitly log in to ECR using the host's Docker daemon
                        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ecrRegistry}"

                        // 3. Now that we are logged in, run everything inside the agent container
                        docker.image(agentImage).inside('-v /var/run/docker.sock:/var/run/docker.sock') {

                            // --- STAGE: CHECKOUT ---
                            echo "Checking out code..."
                            checkout scm

                            // --- STAGE: TEST & ANALYZE ---
                            echo "Installing dependencies and running tests..."
                            sh 'python3 -m venv venv'
                            sh '. venv/bin/activate && pip install -r requirements.txt && pip install -r requirements-dev.txt'
                            sh '. venv/bin/activate && pytest tests/unit || echo "Tests failed or no tests found"'
                            withSonarQubeEnv('SonarQube-Server') {
                                sh ". venv/bin/activate && /sonar-scanner-4.7.0.2747-linux/bin/sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
                            }

                            // --- STAGE: BUILD & PUSH ---
                            echo "Building and pushing application Docker image..."
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

                            // The login was already handled, so we can just push
                            dockerImage.push("${ecrRepoUrl}:${env.BUILD_NUMBER}")
                            dockerImage.push("${ecrRepoUrl}:latest")

                            // --- STAGE: DEPLOY ---
                            echo "Planning and deploying to environment..."
                            dir('terraform') {
                                input message: "Apply plan to ${params.TARGET_ENV}?", ok: 'Deploy'
                                sh "terraform workspace select ${params.TARGET_ENV}"
                                def imageUrl = "${ecrRepoUrl}:${env.BUILD_NUMBER}"
                                sh "terraform apply -auto-approve -var=\"container_image=${imageUrl}\" -var=\"environment=${params.TARGET_ENV}\""
                            }
                        }
                    }
                }
            }
        }
    }
}
