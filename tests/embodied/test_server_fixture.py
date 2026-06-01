from urllib.request import urlopen


def test_local_server_serves_sample_form(local_server):
    with urlopen(f"{local_server}/sample_form.html") as response:
        html = response.read().decode("utf-8")

        assert response.status == 200
        assert "aria-label" in html
        assert "搜索" in html or "search" in html
