"""Printable rendering of the same reference chapters shown in the app."""
from html import escape


def sheet_terms(entries):
    for term, idea in entries:
        yield f"<dt>{escape(term)}</dt><dd>{escape(idea)}</dd>"


def printable_sheet(title, entries):
    return "\n".join((
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        f"<title>{escape(title)} · Rust cheat sheet</title>",
        "<style>@page { margin: 17mm; } body { max-width: 42rem; margin: 2rem auto; padding: 0 1rem; "
        "font: 11pt/1.45 sans-serif; } h1, dt { break-after: avoid; } "
        "dt { font-weight: bold; } dd { margin: 0 0 1rem; } "
        "@media print { body { margin: 0; padding: 0; } }</style>",
        f"<main><h1>{escape(title)}</h1><p>Rust cheat sheet</p><dl>",
        *sheet_terms(entries), "</dl></main></html>",
    ))


def printable_reference(chapters, milestones=()):
    style = """
        body { max-width: 44rem; margin: 2rem auto; padding: 0 1rem;
               color: #171717; font: 11pt/1.55 sans-serif; }
        h1, h2, h3 { break-after: avoid; line-height: 1.2; }
        h2 { margin-top: 2rem; }
        dt { font-weight: bold; break-after: avoid; }
        dd { margin: 0 0 .75rem; }
        pre { border: 1px solid #777; padding: .75rem; white-space: pre-wrap;
              overflow-wrap: anywhere; break-inside: avoid; }
        a { color: #19486a; overflow-wrap: anywhere; }
        @media print { body { margin: 0; padding: 0; } h2 { break-before: page; } }
        @page { margin: 17mm; }
    """
    content = [
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        f'<title>Rust companion reference</title><style>{style}</style><main>',
        '<h1>Rust companion reference</h1><h2 class="contents">Contents</h2>',
        '<style>@media print { h2.contents { break-before: auto; } }</style><ol>',
    ]
    for chapter in chapters:
        content.append(f'<li><a href="#{escape(chapter.id)}">{escape(chapter.title)}</a></li>')
    if milestones:
        content.append('<li><a href="#course-sheets">Course cheat sheets</a></li>')
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
        content.append('</ul><h3>Cheat sheet</h3><dl>')
        content.extend(sheet_terms(chapter.cheat_sheet))
        content.append('</dl></section>')
    if milestones:
        content.append('<section id="course-sheets"><h2>Course cheat sheets</h2>')
        for stage in milestones:
            content.append(f'<h3>{escape(stage.title)}</h3><dl>')
            content.extend(sheet_terms(stage.cheat_sheet))
            content.append('</dl>')
        content.append('</section>')
    content.append('</main></html>')
    return "\n".join(content)


def print_sheet(window, title, entries, pdf_path=None):
    import gi

    gi.require_foreign("cairo")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Gtk, Pango, PangoCairo

    operation = Gtk.PrintOperation()
    operation.set_job_name(f"Rust Tutor · {title}")
    operation.set_unit(Gtk.Unit.POINTS)
    operation.set_n_pages(1)

    def draw(_operation, context, _page):
        cairo = context.get_cairo_context()
        cairo.set_source_rgb(0, 0, 0)
        layout = context.create_pango_layout()
        layout.set_width(int(context.get_width() * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        y = 0
        lines = [(title, "Sans Bold 18", 5), ("Rust cheat sheet", "Sans 11", 18)]
        for term, idea in entries:
            lines.extend(((term, "Sans Bold 11", 4), (idea, "Sans 11", 12)))
        for value, font, spacing in lines:
            layout.set_text(value, -1)
            layout.set_font_description(Pango.FontDescription.from_string(font))
            cairo.move_to(0, y)
            PangoCairo.show_layout(cairo, layout)
            y += layout.get_size()[1] / Pango.SCALE + spacing

    operation.connect("draw-page", draw)
    action = Gtk.PrintOperationAction.PRINT_DIALOG
    if pdf_path is not None:
        operation.set_export_filename(pdf_path)
        action = Gtk.PrintOperationAction.EXPORT
    return operation.run(action, window) == Gtk.PrintOperationResult.APPLY
