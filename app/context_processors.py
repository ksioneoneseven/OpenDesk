from flask import g
from app.models import Setting

def inject_settings():
    """
    Inject settings into the application context.
    This makes settings available to all templates.
    """
    # Get theme setting
    theme_setting = Setting.query.filter_by(key='theme').first()
    if theme_setting:
        g.theme = theme_setting.value
    else:
        g.theme = 'light'  # Default to light mode
    
    return {}
