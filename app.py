"""Public StoryScout Lite website for Render or other Python hosting."""
from pathlib import Path
import os
import gradio as gr
from lite_ui import init_app

BASE = Path(__file__).resolve().parent
STORY_CSS = (BASE / 'storyscout.css').read_text(encoding='utf-8')
STORY_THEME = gr.themes.Soft(primary_hue='emerald', secondary_hue='green', neutral_hue='slate')

GRADIO_MAJOR = int(gr.__version__.split('.')[0])
app = init_app(BASE, theme=STORY_THEME, css=STORY_CSS)

if __name__ == '__main__':
    kwargs = {}
    if GRADIO_MAJOR >= 6:
        kwargs.update(theme=STORY_THEME, css=STORY_CSS)
    app.launch(
        server_name='0.0.0.0',
        server_port=int(os.environ.get('PORT', '7860')),
        show_error=True,
        max_file_size='80mb',
        **kwargs,
    )
