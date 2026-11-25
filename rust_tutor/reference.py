"""Printable rendering of the same reference chapters shown in the app."""
from html import escape


def printable_reference(chapters):
    style = """
        body { max-width: 44rem; margin: 2rem auto; padding: 0 1rem;
               color: #171717; font: 11pt/1.55 sans-serif; }
        h1, h2, h3 { break-after: avoid; line-height: 1.2; }
        h2 { margin-top: 2rem; }
        pre { border: 1px solid #777; padding: .75rem; white-space: pre-wrap;
              overflow-wrap: anywhere; break-inside: avoid; }
        a { color: #19486a; overflow-wrap: anywhere; }
        @media print { body { margin: 0; padding: 0; } h2 { break-before: page; } }
        @page { margin: 17mm; }
    """
    content = [
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        f'<title>Rust companion reference</title><style>{style}</style><main>',
        '<h1>Rust companion reference</h1><p>Beginner Rust · First milestone</p><h2 class="contents">Contents</h2>',
        '<style>@media print { h2.contents { break-before: auto; } }</style><ol>',
    ]
    for chapter in chapters:
        content.append(f'<li><a href="#{escape(chapter.id)}">{escape(chapter.title)}</a></li>')
    content.append('</ol>')
    for chapter in chapters:
        content.append(f'<section id="{escape(chapter.id)}"><h2>{escape(chapter.title)}</h2>')
        content.append(f'<p>{escape(chapter.summary)}</p>')
        for title, text in chapter.sections:
            content.append(f'<h3>{escape(title)}</h3><p>{escape(text)}</p>')
        content.append(f'<h3>Example</h3><pre>{escape(chapter.example)}</pre><h3>Sources</h3><ul>')
        for title, url in chapter.sources:
            safe_url = escape(url, quote=True)
            content.append(f'<li>{escape(title)}. <a href="{safe_url}">{safe_url}</a></li>')
        content.append('</ul></section>')
    content.append('</main></html>')
    return "\n".join(content)
