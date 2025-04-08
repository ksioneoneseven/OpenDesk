from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from config import Config
import jinja2
import markupsafe

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail = Mail()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.tickets import bp as tickets_bp
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    
    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    from app.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
    
    from app.assets import bp as assets_bp
    app.register_blueprint(assets_bp, url_prefix='/assets')
    
    from app.time_expenses import bp as time_expenses_bp
    app.register_blueprint(time_expenses_bp, url_prefix='/time-expenses')
    
    # Register context processors
    from app.context_processors import inject_settings
    app.context_processor(inject_settings)
    
    from app.knowledge_base import bp as kb_bp
    app.register_blueprint(kb_bp, url_prefix='/kb')
    
    # Error handlers
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)
    
    # Add custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br(value):
        """Convert newlines to HTML line breaks."""
        if not value:
            return ''
        result = markupsafe.escape(value).replace('\n', markupsafe.Markup('<br>'))
        return markupsafe.Markup(result)
    
    # Create database tables on first run
    with app.app_context():
        db.create_all()
        from app.models import User, Role
        
        # Create default roles if they don't exist
        if not Role.query.filter_by(name='Administrator').first():
            admin_role = Role(name='Administrator', description='Full access to all features')
            db.session.add(admin_role)
        
        if not Role.query.filter_by(name='Agent').first():
            agent_role = Role(name='Agent', description='Can manage tickets and knowledge base')
            db.session.add(agent_role)
            
        # Create default admin user if no users exist
        if not User.query.first():
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin_user = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                password_hash=bcrypt.generate_password_hash('12345678').decode('utf-8'),
                role=admin_role,
                is_active=True,
                force_password_change=True
            )
            db.session.add(admin_user)
            
        db.session.commit()
    
    return app
