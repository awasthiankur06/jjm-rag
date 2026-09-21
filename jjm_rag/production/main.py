from __future__ import annotations

from .cli import build_service

try:
	from .api import create_app
except RuntimeError:
	app = None
else:
	try:
		app = create_app(build_service())
	except RuntimeError:
		app = None
