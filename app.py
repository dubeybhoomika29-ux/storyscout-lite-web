"""Public StoryScout Lite website for Render or other Python hosting."""
from pathlib import Path
import os
from lite_ui import init_app

BASE = Path(__file__).resolve().parent
app = init_app(BASE)

if __name__ == '__main__':
    app.launch(
        server_name='0.0.0.0',
        server_port=int(os.environ.get('PORT', '7860')),
        show_error=True,
        max_file_size='80mb',
    )
