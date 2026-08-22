from fastapi.testclient import TestClient

from app.main import STATIC_DIR, TEMPLATES_DIR, app


def test_design_system_tokens_and_architecture():
    # 1. Verify app.css contains canonical tokens
    app_css_path = STATIC_DIR / "css" / "app.css"
    assert app_css_path.exists()
    content = app_css_path.read_text(encoding="utf-8")

    assert "--color-brand-primary" in content
    assert "--bg-canvas" in content
    assert "--bg-surface" in content
    assert "--radius-2xl" in content
    assert "--transition-fast" in content
    assert "html.dark" in content
    assert "@media (prefers-reduced-motion: reduce)" in content


def test_templates_inherit_centralized_design_system():
    # 2. Verify base templates reference centralized app.css with versioning
    base_html = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    enterprise_base_html = (TEMPLATES_DIR / "enterprise_base.html").read_text(encoding="utf-8")

    assert "/static/css/app.css?v=" in base_html
    assert "/static/css/app.css?v=" in enterprise_base_html
    assert 'class="dark"' in base_html
    assert 'class="dark"' in enterprise_base_html


def test_pages_render_with_design_system_classes():
    client = TestClient(app)

    # 3. Test major routes return Stitch design system markup
    routes_to_test = ["/", "/calculator", "/help"]
    for route in routes_to_test:
        res = client.get(route)
        assert res.status_code == 200
        assert "app.css" in res.text
        assert "bg-slate-900" in res.text or "glass-card" in res.text or "btn-primary" in res.text

