from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
from .config import settings
import logging

logger = logging.getLogger("ssp-search-service")

opensearch_client = None

def get_opensearch_client():
    global opensearch_client
    if not opensearch_client:
        try:
            logger.info(f"Connecting to OpenSearch at {settings.OPENSEARCH_HOST}")
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key, 
                credentials.secret_key, 
                settings.AWS_REGION, 
                settings.SERVICE, 
                session_token=credentials.token
            )
            
            opensearch_client = OpenSearch(
                hosts=[{'host': settings.OPENSEARCH_HOST, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
        except Exception as e:
            logger.critical(f"Failed to connect to OpenSearch: {e}")
            raise
    return opensearch_client
