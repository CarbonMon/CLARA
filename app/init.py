from flask import Flask
from flask_session import Session
import os

session = Session()

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    if test_config is None:
        app.config.from_object('app.config.Config')
    else:
        app.config.from_mapping(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize session
    session.init_app(app)
    
    # Register blueprints
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app
