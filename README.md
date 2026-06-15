# SSP Search Service

The Smart Shop Platform Search Service. This service is built with FastAPI and integrates with Amazon OpenSearch Serverless (or a standard OpenSearch cluster) to provide fast, vector-based semantic search for products.

## Technologies Used
*   **Python 3.12**
*   **FastAPI:** High-performance web framework.
*   **OpenSearch-py:** Client for interacting with the OpenSearch cluster.
*   **Terraform:** Infrastructure as Code (fetches modules from `ssp-infra-modules`).
*   **Docker:** Containerization.
*   **Jenkins:** CI/CD pipeline.

## Infrastructure Setup
This service relies on the core OpenSearch infrastructure. Ensure the `opensearch` module from the shared terraform library has been applied.

## Development

1.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```
2.  Set environment variables:
    ```bash
    export OPENSEARCH_HOST="your-opensearch-endpoint.region.es.amazonaws.com"
    export AWS_REGION="us-east-1"
    ```
3.  Run the application:
    ```bash
    uvicorn app.main:app --reload
    ```
