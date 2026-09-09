# backend/app.py

from flask import Flask
from config import Config
from extensions import db, bcrypt, jwt, socketio, cors

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.volunteer import volunteer_bp
from routes.participant import participant_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})
    socketio.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(admin_bp,       url_prefix="/api/admin")
    app.register_blueprint(volunteer_bp,   url_prefix="/api/volunteer")
    app.register_blueprint(participant_bp, url_prefix="/api/participant")

    # Register SocketIO handlers (import triggers decorator registration)
    import sockets.occupancy  # noqa: F401
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200
    
    # Create tables
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(
        app,
        debug=Config.FLASK_DEBUG,
        port=Config.FLASK_PORT
    )