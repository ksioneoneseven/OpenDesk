from flask import Blueprint

bp = Blueprint('knowledge_base', __name__)

from app.knowledge_base import routes
