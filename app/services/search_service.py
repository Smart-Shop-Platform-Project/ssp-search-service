from ..core.opensearch_client import get_opensearch_client
import logging

logger = logging.getLogger("ssp-search-service")

class SearchService:
    def __init__(self):
        self.client = get_opensearch_client()

    async def search_products(self, query: str, size: int = 10):
        search_body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description", "category"]
                }
            }
        }
        try:
            logger.info(f"Searching for products with query: {query}")
            response = self.client.search(
                index="products",
                body=search_body
            )
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
