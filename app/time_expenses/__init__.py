from flask import Blueprint

bp = Blueprint('time_expenses', __name__)

from app.time_expenses import routes
