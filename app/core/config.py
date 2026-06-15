from pydantic_settings import BaseSettings
import os
import boto3
import logging

logger = logging.getLogger("ssp-search-service")

def get_ssm_parameter(name, region):
    try:
        ssm_client = boto3.client('ssm', region_name=region)
        parameter = ssm_client.get_parameter(Name=name, WithDecryption=True)
        return parameter['Parameter']['Value']
    except Exception as e:
        logger.critical(f"Error fetching parameter {name}: {e}")
        raise

class Settings(BaseSettings):
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
    OPENSEARCH_HOST_PARAM_NAME: str = os.environ.get("OPENSEARCH_HOST_PARAM_NAME", "/ssp/search/opensearch_host")
    OPENSEARCH_HOST: str = ""
    SERVICE: str = 'es'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.OPENSEARCH_HOST = get_ssm_parameter(self.OPENSEARCH_HOST_PARAM_NAME, self.AWS_REGION)
        except Exception:
             self.OPENSEARCH_HOST = "localhost"

settings = Settings()
