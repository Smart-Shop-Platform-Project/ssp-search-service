import pytest
from unittest.mock import patch, MagicMock
from app.services.search_service import SearchService

# Dummy settings
class DummySettings:
    AWS_REGION = "us-east-1"
    OPENSEARCH_HOST = "test-host"
    SERVICE = 'es'

@pytest.fixture
def mock_opensearch_client():
    with patch("app.services.search_service.get_opensearch_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def search_service(mock_opensearch_client):
    with patch("app.services.search_service.settings", DummySettings()):
        return SearchService()

@pytest.mark.asyncio
async def test_search_products_success(search_service, mock_opensearch_client):
    # Setup mock response
    mock_opensearch_client.search.return_value = {
        'hits': {
            'hits': [
                {'_source': {'id': '1', 'name': 'Laptop'}},
                {'_source': {'id': '2', 'name': 'Phone'}}
            ]
        }
    }

    # Execute
    results = await search_service.search_products("electronics", size=2)

    # Assert
    assert len(results) == 2
    assert results[0]['name'] == 'Laptop'
    mock_opensearch_client.search.assert_called_once()
    
    # Verify the search body
    call_args = mock_opensearch_client.search.call_args[1]
    assert call_args['index'] == 'products'
    assert call_args['body']['size'] == 2
    assert call_args['body']['query']['multi_match']['query'] == 'electronics'

@pytest.mark.asyncio
async def test_search_products_error(search_service, mock_opensearch_client):
    # Setup mock to raise an exception
    mock_opensearch_client.search.side_effect = Exception("OpenSearch connection failed")

    # Execute and Assert
    with pytest.raises(Exception) as exc_info:
        await search_service.search_products("test")
    
    assert "OpenSearch connection failed" in str(exc_info.value)
