import pytest


@pytest.fixture
def static_client(app, tmp_path):
    """A client whose static folder holds a tiny fake frontend build, so these
    tests work in CI where the real build/ directory does not exist."""
    (tmp_path / 'index.html').write_text('<html>SPA shell</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log(1)')
    app.static_folder = str(tmp_path)
    return app.test_client()


class TestStaticFiles:
    def test_root_serves_index(self, static_client):
        response = static_client.get('/')
        assert response.status_code == 200
        assert b'SPA shell' in response.data

    def test_serves_static_assets(self, static_client):
        response = static_client.get('/assets/app.js')
        assert response.status_code == 200
        assert response.data == b'console.log(1)'


class TestClientSideRoutes:
    """The React app routes /config itself; a refresh or deep link asks the
    server for that path, which must return the app shell rather than 404."""

    @pytest.mark.parametrize('path', ['/config', '/config/', '/some/deep/route'])
    def test_unknown_page_paths_serve_the_app_shell(self, static_client, path):
        response = static_client.get(path)
        assert response.status_code == 200
        assert b'SPA shell' in response.data

    def test_head_request_is_served_too(self, static_client):
        assert static_client.head('/config').status_code == 200

    def test_unknown_api_paths_stay_404(self, static_client):
        response = static_client.get('/api/nope')
        assert response.status_code == 404
        assert b'SPA shell' not in response.data

    @pytest.mark.parametrize('path', ['/assets/missing.js', '/favicon.ico'])
    def test_missing_files_stay_404_instead_of_returning_html(self, static_client, path):
        response = static_client.get(path)
        assert response.status_code == 404
        assert b'SPA shell' not in response.data

    def test_non_get_requests_are_not_served_the_shell(self, static_client):
        response = static_client.post('/config')
        assert response.status_code != 200
        assert b'SPA shell' not in response.data

    def test_without_a_build_it_is_a_plain_404_not_a_server_error(self, app, tmp_path):
        app.static_folder = str(tmp_path)  # exists, but has no index.html
        assert app.test_client().get('/config').status_code == 404
