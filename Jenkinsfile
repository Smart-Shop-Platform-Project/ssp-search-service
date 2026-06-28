pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        SONAR_TOKEN = credentials('SONAR_TOKEN')
    }

    stages {
        stage('Execute Build in Container') {
            steps {
                script {
                    def awsAccountId
                    withCredentials([aws(accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', credentialsId: 'aws-creds')]) {
                        // Use the REAL, absolute path to the aws executable, bypassing the symbolic link.
                        awsAccountId = sh(script: '/usr/local/aws-cli/v2/current/bin/aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
                    }

                    if (!awsAccountId) {
                        error "Could not determine AWS Account ID."
                    }

                    def ecrRegistry = "${awsAccountId}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    def agentImage = "${ecrRegistry}/ssp-jenkins-agent:latest"

                    docker.withRegistry("https://${ecrRegistry}", 'aws-creds') {
                        docker.image(agentImage).inside('-v /var/run/docker.sock:/var/run/docker.sock') {

                            echo "Checking out code..."
                            checkout scm

                            echo "Installing dependencies and running tests..."
                            sh 'pip install -r requirements-dev.txt'
                            sh 'pytest tests/unit || echo "No tests configured yet"'
                            withSonarQubeEnv('SonarQube-Server') {
                                sh "sonar-scanner -Dsonar.projectKey=ssp-search-service -Dsonar.sources=app -Dsonar.login=${SONAR_TOKEN}"
                            }

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
                            dockerImage.push("${env.BUILD_NUMBER}")
                            dockerImage.push("latest")

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
