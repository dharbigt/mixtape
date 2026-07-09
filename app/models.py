from app import db
from flask_login import UserMixin
from datetime import datetime


class User(UserMixin, db.Model):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    picture_url = db.Column(db.String(500), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Mixtape(db.Model):
    """Mixtape metadata"""
    __tablename__ = 'mixtape'
    
    mixtape_id = db.Column(db.String(255), primary_key=True, unique=True)
    user = db.Column(db.String(255), index=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    language = db.Column(db.String(50))
    copyright = db.Column(db.String(255))
    lastBuildDate = db.Column(db.Integer)
    pubDate = db.Column(db.Integer)
    docs = db.Column(db.String(255))
    webMasterEmail = db.Column(db.String(255))
    author = db.Column(db.String(255))
    authorEmail = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    summary = db.Column(db.Text)
    category = db.Column(db.String(255))
    explicit = db.Column(db.Integer, default=0)
    hidden = db.Column(db.Integer, default=0)
    
    # Style customization fields
    style_shell_color = db.Column(db.String(7), default='#ff9100')
    style_shell_opacity = db.Column(db.Float, default=0.3)
    style_reel_color = db.Column(db.String(7), default='#ff9100')
    style_reel_opacity = db.Column(db.Float, default=1.0)
    style_clip_color = db.Column(db.String(7), default='#ff9100')
    style_clip_opacity = db.Column(db.Float, default=1.0)
    style_guide_color = db.Column(db.String(7), default='#8e8e8e')
    style_guide_opacity = db.Column(db.Float, default=1.0)
    style_label_color = db.Column(db.String(7), default='#ffffff')
    style_label_opacity = db.Column(db.Float, default=1.0)
    style_meter_color = db.Column(db.String(7), default='#ff9100')
    style_meter_opacity = db.Column(db.Float, default=0.3)
    style_screw_color = db.Column(db.String(7), default='#8e8e8e')
    style_screw_star_opacity = db.Column(db.Float, default=0.3)
    
    # Label display mode
    label_display_mode = db.Column(db.String(50), default='Top and Bottom Labels')
    
    # Label text fields
    label_upper_text = db.Column(db.String(255), default='')
    label_lower_text = db.Column(db.String(255), default='')
    label_font_family = db.Column(db.String(100), default='Arial')
    label_upper_font_size = db.Column(db.Integer, default=12)
    label_lower_font_size = db.Column(db.Integer, default=10)
    label_upper_opacity = db.Column(db.Float, default=1.0)
    label_lower_opacity = db.Column(db.Float, default=1.0)
    
    # Overlay image
    overlay_filename = db.Column(db.String(255), default=None)
    
    # Relationship to tracks
    tracks = db.relationship('Track', backref='mixtape', lazy='joined', foreign_keys='Track.mixtape_id', primaryjoin='Mixtape.mixtape_id==Track.mixtape_id')
    
    def __repr__(self):
        return f'<Mixtape {self.mixtape_id}>'


class Track(db.Model):
    """Mixtape track item"""
    __tablename__ = 'track'
    
    track_id = db.Column(db.String(255), primary_key=True, unique=True)
    mixtape_id = db.Column(db.String(255), index=True)
    user = db.Column(db.String(255), index=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    length = db.Column(db.Integer)
    category = db.Column(db.String(255))
    pubDate = db.Column(db.Integer)
    author = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    summary = db.Column(db.Text)
    duration = db.Column(db.Integer)
    keywords = db.Column(db.String(500))
    sequence = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Track {self.track_id}>'



