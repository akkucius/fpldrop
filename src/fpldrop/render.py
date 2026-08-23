from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from playwright.sync_api import sync_playwright

from fpldrop.fpl import TeamSnapshot

VIEWPORT = {"width": 1080, "height": 1800}


def render_card(snapshot: TeamSnapshot, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _render_html(snapshot)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport=VIEWPORT,
            device_scale_factor=2,
        )
        page.set_content(html, wait_until="domcontentloaded")
        page.evaluate(
            """
            async () => {
              if (document.fonts && document.fonts.ready) {
                await document.fonts.ready;
              }
              const images = Array.from(document.images);
              await Promise.all(images.map((img) => {
                if (img.complete) return Promise.resolve();
                return new Promise((resolve) => {
                  img.addEventListener('load', resolve, { once: true });
                  img.addEventListener('error', resolve, { once: true });
                });
              }));
            }
            """
        )
        page.locator(".card").screenshot(path=str(output_path), type="png")
        browser.close()

    return output_path


def _render_html(snapshot: TeamSnapshot) -> str:
    env = Environment(
        loader=PackageLoader("fpldrop", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("team_card.html")
    return template.render(team=snapshot)


def template_path() -> Path:
    return Path(str(files("fpldrop").joinpath("templates/team_card.html")))
