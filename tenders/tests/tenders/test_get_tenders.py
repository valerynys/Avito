import requests

import pytest
import requests


@pytest.mark.integration
def test_get_tenders_invalid_query():
    base_url = "http://localhost:8080/api"

    params = {
        "limit": -1,
        "offset": "invalid_offset",
        "service_type": "invalid_service_type"
    }

    response = requests.get(f"{base_url}/tenders", params=params)

    assert response.status_code == 400, f"Expected status code 400, got {response.status_code}"

