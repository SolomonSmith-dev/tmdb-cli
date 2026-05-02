import pytest
from unittest.mock import patch, MagicMock
from tmdb_cli.client import TMDBClient, BASE_URL


class TestTMDBClient:
    def setup_method(self):
        self.client = TMDBClient(api_key="test-key")

    @patch("tmdb_cli.client.requests.get")
    def test_url_construction(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        self.client.get_movies("popular", page=2)

        mock_get.assert_called_once_with(
            f"{BASE_URL}/movie/popular",
            params={"page": 2, "api_key": "test-key"},
            timeout=10,
        )

    @patch("tmdb_cli.client.requests.get")
    def test_search_url_construction(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        self.client.search_movies("inception", page=2)

        mock_get.assert_called_once_with(
            f"{BASE_URL}/search/movie",
            params={"query": "inception", "page": 2, "api_key": "test-key"},
            timeout=10,
        )

    @patch("tmdb_cli.client.requests.get")
    def test_search_network_error_raises_runtime(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(RuntimeError, match="Network/API error"):
            self.client.search_movies("inception")

    @patch("tmdb_cli.client.requests.get")
    def test_api_key_in_params(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        self.client.get_movies("top")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["api_key"] == "test-key"

    def test_invalid_category_raises(self):
        with pytest.raises(KeyError):
            self.client.get_movies("nonexistent")

    @patch("tmdb_cli.client.requests.get")
    def test_network_error_raises_runtime(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(RuntimeError, match="Network/API error"):
            self.client.get_movies("popular")

    @patch("tmdb_cli.client.requests.get")
    def test_http_error_raises_runtime(self, mock_get):
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("401 Unauthorized")
        mock_get.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Network/API error"):
            self.client.get_movies("popular")

    @patch("tmdb_cli.client.requests.get")
    def test_api_key_redacted_in_error(self, mock_get):
        import requests as req

        leaky_msg = (
            "401 Client Error: Unauthorized for url: "
            "https://api.themoviedb.org/3/movie/popular?page=1&api_key=SECRET123"
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError(leaky_msg)
        mock_get.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            self.client.get_movies("popular")

        assert "SECRET123" not in str(exc_info.value)
        assert "api_key=***REDACTED***" in str(exc_info.value)
