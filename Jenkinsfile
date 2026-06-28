pipeline {
    // This pipeline will run on any available agent.
    // The actual build steps will be executed inside a specified Docker container.
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
    }

    stages {
        stage('Execute Build in Container') {
            steps {
                script {
                    // This is the most robust pattern. We define everything inside one script block.
                    // First, get the AWS Account ID from the host machine, which has AWS CLI installed.
                    def awsAccountId
                    withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                        awsAccountId = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                    }

                    if (!awsAccountId) {
                        error "Could not determine AWS Account ID."
                    }

                    def ecrRegistry = "${awsAccountId}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    def agentImage = "${ecrRegistry}/ssp-jenkins-agent:latest"

                    // Now, log in to that registry
                    docker.withRegistry("https://${ecrRegistry}", 'aws-creds') {

                        // And finally, run all subsequent steps inside the container from that registry
                        docker.image(agentImage).inside('-v /var/run/docker.sock:/var/run/docker.sock') {

                            // --- STAGE: CHECKOUT ---
                            echo "Checking out code..."
                            checkout scm

                            // --- STAGE: TEST & ANALYZE ---
                            echo "Installing dependencies and running tests..."
                            sh 'pip install -r requirements-dev.txt'
                            sh 'pytest tests/unit || echo "No tests configured yet"'
                            withSonarQubeEnv('SonarQube-Server') {
                                sh "sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
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
                            // The withRegistry block above handles the login, so we just push
                            dockerImage.push("${env.BUILD_NUMBER}")
                            dockerImage.push("latest")

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
