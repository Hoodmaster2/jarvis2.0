import sys
sys.path.insert(0, '.')
from api.server import create_app
import uvicorn
app = create_app()
uvicorn.run(app, host='127.0.0.1', port=8765, log_level='info')
