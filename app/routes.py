from flask import Blueprint, render_template, redirect, url_for, request, Response, jsonify, current_app, send_from_directory
from flask_login import login_user, logout_user, current_user
from app.oauth import oauth
from app.models import User, Mixtape, Track
from app import db
import os
from werkzeug.utils import secure_filename
import hashlib
import secrets
from datetime import datetime

main_bp = Blueprint('main', __name__)

# Temporary file storage for uploads
UPLOAD_FOLDER = '/tmp/podcast_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def write_trck_tag(filepath, track_number, total_tracks=None, album_name=None):
    """Write TRCK/trkn and optionally TALB/©alb tags, preserving all other tags"""
    import sys
    try:
        if filepath.lower().endswith('.mp3'):
            from mutagen.id3 import ID3, TRCK, TALB
            try:
                audio = ID3(filepath)
            except Exception:
                audio = ID3()
            trck_value = f"{track_number}/{total_tracks}" if total_tracks else str(track_number)
            audio['TRCK'] = TRCK(encoding=3, text=trck_value)
            if album_name:
                audio['TALB'] = TALB(encoding=3, text=album_name)
            audio.save(filepath)
            print(f"[write_trck_tag] Written TRCK={trck_value} TALB={album_name!r} to {filepath}", file=sys.stderr)
        elif filepath.lower().endswith(('.m4a', '.aac')):
            from mutagen.mp4 import MP4
            audio = MP4(filepath)
            audio['trkn'] = [(track_number, total_tracks or 0)]
            if album_name:
                audio['\xa9alb'] = [album_name]
            audio.save()
            print(f"[write_trck_tag] Written trkn={track_number}/{total_tracks} alb={album_name!r} to {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"[write_trck_tag] Error writing tags to {filepath}: {e}", file=sys.stderr)


def generate_mixtape_id():
    """Generate a unique mixtape ID using hash subsegment"""
    # Create a random token and use first 8 chars of its hash
    random_token = secrets.token_hex(16)
    hash_id = hashlib.sha256(random_token.encode()).hexdigest()[:12]
    return f"mt_{hash_id}"


def cleanup_orphaned_files():
    """Delete any files in static/ that don't match an episode's ID"""
    import sys
    
    try:
        static_dirs = [
            os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks'),
            os.path.join(current_app.config['DOCROOT'], 'app/static', 'artwork')
        ]
        
        # Get all track IDs from database
        tracks = Track.query.all()
        valid_ids = set(t.track_id for t in tracks)
        
        for static_dir in static_dirs:
            if not os.path.exists(static_dir):
                continue
            
            for filename in os.listdir(static_dir):
                filepath = os.path.join(static_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                
                # Extract base filename without extension
                base_filename = os.path.splitext(filename)[0]
                
                # Never delete mixtape images (mt_*) - they are tied to mixtapes, not tracks
                if base_filename.startswith('mt_'):
                    continue
                
                # Check if this file's ID exists in database
                if base_filename not in valid_ids:
                    try:
                        os.remove(filepath)
                        print(f"[cleanup_orphaned_files] Deleted orphaned file: {filepath}", file=sys.stderr)
                    except Exception as e:
                        print(f"[cleanup_orphaned_files] Error deleting {filepath}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[cleanup_orphaned_files] Error during cleanup: {e}", file=sys.stderr)


@main_bp.route('/')
def index():
    """Home page - landing page for guests, mixtape list for authenticated users"""
    if not current_user.is_authenticated:
        return render_template('index.html', mixtapes=None)
    mixtapes = Mixtape.query.all()
    return render_template('index.html', mixtapes=mixtapes)


@main_bp.route('/mixtape/<mixtape_id>/cassette.svg')
def mixtape_cassette_svg(mixtape_id):
    """Generate cassette SVG with custom styles applied"""
    from flask import Response
    
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first_or_404()
    
    # Read the base cassette-new.svg template
    svg_path = os.path.join(current_app.config['DOCROOT'], 'app/static/cassette-new.svg')
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    
    # Get default values
    shell_color = mixtape.style_shell_color if mixtape.style_shell_color else '#fc4c4c'
    shell_opacity = mixtape.style_shell_opacity if mixtape.style_shell_opacity is not None else 0.64
    
    reel_color = mixtape.style_reel_color if mixtape.style_reel_color else '#00ff00'
    reel_opacity = mixtape.style_reel_opacity if mixtape.style_reel_opacity is not None else 1.0
    
    clip_color = mixtape.style_clip_color if mixtape.style_clip_color else '#00ff00'
    clip_opacity = mixtape.style_clip_opacity if mixtape.style_clip_opacity is not None else 1.0
    
    guide_color = mixtape.style_guide_color if mixtape.style_guide_color else '#00ff00'
    guide_opacity = mixtape.style_guide_opacity if mixtape.style_guide_opacity is not None else 1.0
    
    label_color = mixtape.style_label_color if mixtape.style_label_color else '#ffffff'
    label_opacity = mixtape.style_label_opacity if mixtape.style_label_opacity is not None else 1.0
    
    meter_color = mixtape.style_meter_color if mixtape.style_meter_color else '#ff0000'
    meter_opacity = mixtape.style_meter_opacity if mixtape.style_meter_opacity is not None else 0.3
    
    screw_color = mixtape.style_screw_color if mixtape.style_screw_color else '#8e8e8e'
    screw_star_opacity = mixtape.style_screw_star_opacity if mixtape.style_screw_star_opacity is not None else 0.3
    
    overlay_filename = mixtape.overlay_filename
    
    # Determine which labels to display based on label_display_mode
    label_display = mixtape.label_display_mode or 'Top and Bottom Labels'
    
    # Prepare label visibility CSS
    label_css = ''
    if label_display == 'No Label':
        label_css = '#Full_Label, #Upper_Label, #Lower_Label { display: none; }'
    elif label_display == 'Full Label':
        label_css = '#Upper_Label, #Lower_Label { display: none; }'
    elif label_display == 'Top and Bottom Labels':
        label_css = '#Full_Label { display: none; }'
    elif label_display == 'Top Label Only':
        label_css = '#Full_Label, #Lower_Label { display: none; }'
    elif label_display == 'Bottom Label Only':
        label_css = '#Full_Label, #Upper_Label { display: none; }'
    
    # Build custom styles
    styles = f'''
            /* Shell (.st2 class elements) */
            .st2 {{ fill: {shell_color} !important; opacity: {shell_opacity} !important; }}
            /* Reels (.st5 class elements) */
            .st5 {{ fill: {reel_color} !important; opacity: {reel_opacity} !important; }}
            /* Leader clips (.st9 class elements) */
            .st9 {{ fill: {clip_color} !important; opacity: {clip_opacity} !important; }}
            /* Guide spindles (.st7 class elements) */
            .st7 {{ fill: {guide_color} !important; opacity: {guide_opacity} !important; }}
            /* Labels */
            #Full_Label, #Upper_Label, #Lower_Label {{ fill: {label_color} !important; opacity: {label_opacity} !important; }}
            /* Meter bars */
            #Meter .st0 {{ opacity: {meter_opacity} !important; }}
            #Meter rect {{ fill: {meter_color} !important; opacity: {meter_opacity} !important; }}
            /* Screws only (not the star icons) */
            #Screw_SE, #Screw_SW, #Screw_NW, #Screw_NE, #Screw_Middle {{ fill: {screw_color} !important; }}
            /* Screw stars (.st1 class elements) */
            .st1 {{ opacity: {screw_star_opacity} !important; }}
            /* Static tape path */
            .st8 {{ fill: none !important; stroke: #2b1700 !important; }}
            /* Label display mode */
            {label_css}
    '''
    
    # Inject styles into the SVG by replacing the closing </style> tag in defs
    # Find the closing </style> tag and insert our custom styles before </defs>
    svg_content = svg_content.replace('</defs>', f'<style>{styles}</style></defs>')
    
    # Add overlay image if specified
    if overlay_filename:
        overlay_html = f'<image id="tapeOverlay" xlink:href="/static/overlays/{overlay_filename}" x="0" y="0" width="291.42" height="179.61"/>'
        # Insert overlay before Paper_Labels group so it renders behind labels
        svg_content = svg_content.replace('<g id="Paper_Labels">', f'{overlay_html}<g id="Paper_Labels">')
    
    return Response(svg_content, mimetype='image/svg+xml')


@main_bp.route('/login')
def login():
    """Render the login page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('index.html', mixtapes=None)


@main_bp.route('/login/google')
def login_google():
    """Redirect to Google for login"""
    redirect_uri = url_for('main.authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@main_bp.route('/authorize/google')
def authorize_google():
    """Handle Google OAuth callback"""
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        return redirect(url_for('main.index'))
    
    # Find or create user
    user = User.query.filter_by(google_id=user_info.get('sub')).first()
    
    if user:
        # Update user info
        user.email = user_info.get('email')
        user.name = user_info.get('name')
        user.picture_url = user_info.get('picture')
    else:
        # Check if this is the first user
        is_first_user = User.query.count() == 0
        
        # Create new user
        user = User(
            google_id=user_info.get('sub'),
            email=user_info.get('email'),
            name=user_info.get('name'),
            picture_url=user_info.get('picture'),
            is_admin=is_first_user  # First user gets admin privileges
        )
        db.session.add(user)
    
    db.session.commit()
    login_user(user)
    
    return redirect(url_for('main.index'))


@main_bp.route('/admin')
def admin():
    """Admin dashboard - admin users only"""
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    
    mixtapes = Mixtape.query.all()
    return render_template('admin.html', user=current_user, mixtapes=mixtapes)


@main_bp.route('/admin/users')
def admin_users():
    """User management page - admin only"""
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('main.index'))
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', user=current_user, users=users)


@main_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('main.index'))


@main_bp.route('/track/<track_id>/download')
def download_track(track_id):
    """Download an individual track file"""
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))
    track = Track.query.filter_by(track_id=track_id).first_or_404()
    tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
    if os.path.exists(tracks_dir):
        for filename in os.listdir(tracks_dir):
            if filename.startswith(track_id):
                ext = os.path.splitext(filename)[1]
                safe_title = secure_filename(track.title or track_id)
                return send_from_directory(tracks_dir, filename, as_attachment=True,
                                           download_name=f"{safe_title}{ext}")
    return "Track file not found", 404


@main_bp.route('/api/reorder-tracks', methods=['POST'])
def reorder_tracks():
    """Save new track order and update TRCK ID3 tags"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    track_ids = data.get('track_ids', [])
    mixtape_id = data.get('mixtape_id')

    if not track_ids or not mixtape_id:
        return jsonify({'error': 'track_ids and mixtape_id required'}), 400

    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first()
    if not mixtape:
        return jsonify({'error': 'Mixtape not found'}), 404
    if not current_user.is_admin and mixtape.user != current_user.email:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        total = len(track_ids)
        tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
        for i, tid in enumerate(track_ids):
            track = Track.query.filter_by(track_id=tid, mixtape_id=mixtape_id).first()
            if track:
                track.sequence = i + 1
                if os.path.exists(tracks_dir):
                    for filename in os.listdir(tracks_dir):
                        if filename.startswith(tid):
                            write_trck_tag(os.path.join(tracks_dir, filename), i + 1, total, album_name=mixtape.title)
                            break
        mixtape.lastBuildDate = int(datetime.utcnow().timestamp())
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/create-channel', methods=['POST'])
def create_channel():
    """Create a new podcast channel from form submission"""
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('podcast_channel') or not data.get('title'):
            return jsonify({'error': 'Channel ID and Title are required'}), 400
        
        # Check if channel ID already exists
        existing = PodcastChannel.query.filter_by(podcast_channel=data['podcast_channel']).first()
        if existing:
            return jsonify({'error': 'Channel ID already exists'}), 409
        
        # Create new channel
        channel = PodcastChannel(
            podcast_channel=data['podcast_channel'],
            user=current_user.email,
            title=data.get('title', ''),
            description=data.get('description', ''),
            language=data.get('language', 'en'),
            copyright=data.get('copyright', ''),
            author=data.get('author', ''),
            authorEmail=data.get('authorEmail', ''),
            subtitle=data.get('subtitle', ''),
            summary=data.get('summary', ''),
            category=data.get('category', '')
        )
        
        db.session.add(channel)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Channel created successfully',
            'channel_id': channel.podcast_channel,
            'channel_url': f'/channel/{channel.podcast_channel}'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating channel: {str(e)}'}), 500


@main_bp.route('/api/upload-episode', methods=['POST'])
def upload_episode():
    """Upload and extract metadata from episode audio file"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    channel_id = request.form.get('channel_id')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not channel_id:
        return jsonify({'error': 'Channel ID required'}), 400
    
    # Verify channel exists and user has access
    channel = PodcastChannel.query.filter_by(podcast_channel=channel_id).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    # Generate unique episode ID
    episode_id = generate_mixtape_id().replace('mt_', 'ep_')
    
    # Get file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # Create static episodes directory if it doesn't exist
    episodes_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'episodes')
    os.makedirs(episodes_dir, exist_ok=True)
    
    # Save file with episode ID as name
    filename = f"{episode_id}{file_ext}"
    filepath = os.path.join(episodes_dir, filename)
    file.save(filepath)
    
    try:
        # Extract metadata (passing channel and episode IDs for artwork handling)
        metadata = extract_audio_metadata(filepath, channel_id, episode_id)
        metadata['podcast_item'] = episode_id
        metadata['podcast_channel'] = channel_id
        return jsonify(metadata)
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Don't delete - we want to keep the file
        pass


@main_bp.route('/api/create-episode', methods=['POST'])
def create_episode():
    """Create a new podcast episode from form submission"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('podcast_item') or not data.get('title'):
            return jsonify({'error': 'Episode ID and Title are required'}), 400
        
        # Check if episode already exists
        existing = PodcastItem.query.filter_by(podcast_item=data['podcast_item']).first()
        if existing:
            return jsonify({'error': 'Episode already exists'}), 409
        
        # Get current timestamp (Unix timestamp)
        import time
        current_time = int(time.time())
        
        # Use pubDate from metadata if available, otherwise use current time
        pub_date = data.get('pubDate', 0) or current_time
        
        # Create new episode
        episode = PodcastItem(
            podcast_item=data['podcast_item'],
            podcast_channel=data['podcast_channel'],
            user=current_user.email,
            title=data.get('title', ''),
            description=data.get('description', ''),
            author=data.get('author', ''),
            category=data.get('category', ''),
            subtitle=data.get('subtitle', ''),
            summary=data.get('summary', ''),
            duration=data.get('duration', 0),
            keywords=data.get('keywords', ''),
            pubDate=pub_date
        )
        
        db.session.add(episode)
        db.session.commit()
        
        # Clean up any orphaned files after successful creation
        cleanup_orphaned_files()
        
        return jsonify({
            'success': True,
            'message': f'Episode created successfully',
            'episode_id': episode.podcast_item
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating episode: {str(e)}'}), 500


@main_bp.route('/api/update-episode', methods=['POST'])
def update_episode():
    """Update an existing podcast episode"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        podcast_item = data.get('podcast_item')
        
        if not podcast_item:
            return jsonify({'error': 'Episode ID required'}), 400
        
        # Find episode
        episode = PodcastItem.query.filter_by(podcast_item=podcast_item).first()
        if not episode:
            return jsonify({'error': 'Episode not found'}), 404
        
        # Update editable fields
        episode.title = data.get('title', episode.title)
        episode.description = data.get('description', episode.description)
        episode.author = data.get('author', episode.author)
        episode.category = data.get('category', episode.category)
        episode.subtitle = data.get('subtitle', episode.subtitle)
        episode.summary = data.get('summary', episode.summary)
        episode.keywords = data.get('keywords', episode.keywords)
        # Don't update duration - it's read-only
        # Don't update podcast_item - it's the ID
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Episode updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error updating episode: {str(e)}'}), 500


@main_bp.route('/api/delete-episode', methods=['POST'])
def delete_episode():
    """Delete a podcast episode"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        podcast_item = data.get('podcast_item')
        
        if not podcast_item:
            return jsonify({'error': 'Episode ID required'}), 400
        
        # Find episode
        episode = PodcastItem.query.filter_by(podcast_item=podcast_item).first()
        if not episode:
            return jsonify({'error': 'Episode not found'}), 404
        
        # Delete associated files
        import sys
        episodes_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'episodes')
        artwork_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'artwork')
        
        for dir_path in [episodes_dir, artwork_dir]:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.startswith(podcast_item):
                        try:
                            file_path = os.path.join(dir_path, filename)
                            os.remove(file_path)
                            print(f"[delete_episode] Deleted {file_path}", file=sys.stderr)
                        except Exception as e:
                            print(f"[delete_episode] Error deleting file: {e}", file=sys.stderr)
        
        # Delete database record
        db.session.delete(episode)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Episode deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error deleting episode: {str(e)}'}), 500


@main_bp.route('/admin/mixtape/<mixtape_id>', methods=['GET', 'POST'])
def mixtape_admin(mixtape_id):
    """View and edit a mixtape and its tracks"""
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first_or_404()
    
    # Check ownership: user must be admin or own the mixtape
    if not current_user.is_admin and mixtape.user != current_user.email:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Only the owner (or admin) can edit
        if not current_user.is_admin and mixtape.user != current_user.email:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update mixtape fields
        mixtape.title = request.form.get('title', mixtape.title)
        mixtape.description = request.form.get('description', mixtape.description)
        mixtape.author = request.form.get('author', mixtape.author)
        mixtape.language = request.form.get('language', mixtape.language)
        mixtape.category = request.form.get('category', mixtape.category)
        mixtape.subtitle = request.form.get('subtitle', mixtape.subtitle)
        mixtape.summary = request.form.get('summary', mixtape.summary)
        mixtape.copyright = request.form.get('copyright', mixtape.copyright)
        mixtape.lastBuildDate = int(datetime.utcnow().timestamp())
        
        db.session.commit()

        # Update TALB tag on all tracks to match the (possibly new) title
        tracks_all = Track.query.filter_by(mixtape_id=mixtape_id).order_by(Track.sequence.asc(), Track.pubDate.asc()).all()
        tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
        total = len(tracks_all)
        if os.path.exists(tracks_dir):
            for i, t in enumerate(tracks_all):
                for filename in os.listdir(tracks_dir):
                    if filename.startswith(t.track_id):
                        write_trck_tag(os.path.join(tracks_dir, filename), i + 1, total, album_name=mixtape.title)
                        break

        return redirect(url_for('main.mixtape_admin', mixtape_id=mixtape_id))
    
    tracks = Track.query.filter_by(mixtape_id=mixtape_id).order_by(Track.sequence.asc(), Track.pubDate.asc()).all()
    return render_template('mixtape_admin.html', user=current_user, mixtape=mixtape, tracks=tracks)

@main_bp.route('/api/extract-metadata', methods=['POST'])
def extract_metadata():
    """Extract ID3 metadata from uploaded audio file"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    try:
        # Extract metadata using mutagen
        metadata = extract_audio_metadata(filepath)
        return jsonify(metadata)
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Clean up temp file
        try:
            os.remove(filepath)
        except:
            pass


def extract_audio_metadata(filepath, channel_id=None, episode_id=None):
    """Extract ID3 metadata from audio file"""
    import sys
    from mutagen.wave import WAVE
    
    filename = os.path.basename(filepath)
    metadata = {
        'mixtape_id': generate_mixtape_id(),  # Generate unique ID server-side
        'title': '',
        'author': '',
        'category': '',
        'comments': '',
        'copyright': '',
        'description': '',
        'subtitle': '',  # Will be left blank, not populated from file
        'duration': 0,
        'keywords': '',
        'artwork_path': '',  # Path to extracted artwork
        'pubDate': 0  # Unix timestamp from metadata or current time
    }
    
    print(f"[extract_audio_metadata] Processing file: {filepath}", file=sys.stderr)
    print(f"[extract_audio_metadata] File exists: {os.path.exists(filepath)}", file=sys.stderr)
    
    try:
        # Try MP3 (ID3v2)
        if filepath.lower().endswith('.mp3'):
            print(f"[extract_audio_metadata] Detected MP3 file", file=sys.stderr)
            try:
                from mutagen.id3 import ID3
                audio = ID3(filepath)
                
                # Get title from TIT2, fall back to TALB (album)
                metadata['title'] = str(audio.get('TIT2', '')).strip() or str(audio.get('TALB', '')).strip() or ''
                metadata['author'] = str(audio.get('TPE1', '')).strip() or ''  # Artist
                metadata['category'] = str(audio.get('TCON', '')).strip() or ''  # Genre
                metadata['description'] = str(audio.get('TIT3', '')).strip() or ''  # Subtitle
                metadata['summary'] = metadata['description']  # Copy description to summary
                metadata['keywords'] = str(audio.get('TOFN', '')).strip() or ''  # Original filename
                metadata['copyright'] = str(audio.get('TCOP', '')).strip() or ''
                
                # Get duration from mutagen (in seconds)
                from mutagen.mp3 import MP3
                mp3_audio = MP3(filepath)
                metadata['duration'] = int(mp3_audio.info.length)
                
                # Extract artwork if present
                try:
                    from mutagen.id3 import APIC
                    for tag in audio.getall('APIC'):
                        if isinstance(tag, APIC):
                            artwork_path = extract_artwork(filepath, tag.data, 'mp3', channel_id, episode_id)
                            if artwork_path:
                                metadata['artwork_path'] = artwork_path
                            break
                except:
                    pass
                
                print(f"[extract_audio_metadata] MP3 extraction successful", file=sys.stderr)
            except Exception as e:
                print(f"[extract_audio_metadata] MP3 extraction error: {e}", file=sys.stderr)
                pass
        
        # Try MP4 (M4A, AAC)
        elif filepath.lower().endswith(('.m4a', '.aac')):
            print(f"[extract_audio_metadata] Detected MP4 file", file=sys.stderr)
            try:
                from mutagen.mp4 import MP4
                audio = MP4(filepath)
                print(f"[extract_audio_metadata] MP4 tags available: {list(audio.keys())}", file=sys.stderr)
                
                # Pull title from '©nam' (track name)
                metadata['title'] = audio.get('©nam', [''])[0] if audio.get('©nam') else ''
                # Artist
                metadata['author'] = audio.get('©ART', [''])[0] if audio.get('©ART') else ''
                # Genre becomes category
                metadata['category'] = audio.get('©gen', [''])[0] if audio.get('©gen') else ''
                # Description/comments
                metadata['description'] = audio.get('©cmt', [''])[0] if audio.get('©cmt') else ''
                metadata['summary'] = metadata['description']  # Copy description to summary
                # Keywords from grouping tag
                metadata['keywords'] = audio.get('©grp', [''])[0] if audio.get('©grp') else ''
                # Copyright
                metadata['copyright'] = audio.get('cprt', [''])[0] if audio.get('cprt') else ''
                
                # Get duration from mutagen (in seconds)
                metadata['duration'] = int(audio.info.length)
                
                # Extract date from '©day' tag and convert to Unix timestamp
                date_str = audio.get('©day', [''])[0] if audio.get('©day') else ''
                if date_str:
                    try:
                        from datetime import datetime
                        # Try to parse various date formats
                        # Common formats: "YYYY", "YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SSZ"
                        for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d', '%Y']:
                            try:
                                dt = datetime.strptime(date_str, fmt)
                                metadata['pubDate'] = int(dt.timestamp())
                                print(f"[extract_audio_metadata] Parsed date {date_str} to timestamp {metadata['pubDate']}", file=sys.stderr)
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        print(f"[extract_audio_metadata] Error parsing date {date_str}: {e}", file=sys.stderr)
                
                # Extract artwork if present
                try:
                    if 'covr' in audio:
                        artwork_atoms = audio['covr']
                        print(f"[extract_audio_metadata] Found covr atom with {len(artwork_atoms)} images", file=sys.stderr)
                        if artwork_atoms:
                            # Get the first image
                            artwork_atom = artwork_atoms[0]
                            print(f"[extract_audio_metadata] Artwork atom type: {type(artwork_atom)}, size: {len(artwork_atom) if hasattr(artwork_atom, '__len__') else 'unknown'}", file=sys.stderr)
                            artwork_path = extract_artwork(filepath, artwork_atom, 'mp4', channel_id, episode_id)
                            if artwork_path:
                                metadata['artwork_path'] = artwork_path
                    else:
                        print(f"[extract_audio_metadata] No covr tag found in MP4 tags: {list(audio.keys())}", file=sys.stderr)
                except Exception as e:
                    print(f"[extract_audio_metadata] Error extracting MP4 artwork: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                
                print(f"[extract_audio_metadata] MP4 extraction successful: {metadata}", file=sys.stderr)
            except Exception as e:
                print(f"[extract_audio_metadata] MP4 extraction error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                pass
        else:
            print(f"[extract_audio_metadata] Unknown file type: {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"[extract_audio_metadata] Outer exception: {e}", file=sys.stderr)
        pass
    
    print(f"[extract_audio_metadata] Final metadata: {metadata}", file=sys.stderr)
    return metadata


def extract_artwork(filepath, artwork_data, file_type, channel_id=None, episode_id=None):
    """Extract artwork from audio file and save to disk"""
    import sys
    try:
        # Generate artwork path based on episode ID (from filepath)
        base_filename = os.path.splitext(os.path.basename(filepath))[0]
        artwork_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'artwork')
        os.makedirs(artwork_dir, exist_ok=True)
        
        # Handle artwork_data - it might be bytes directly or need extraction
        if hasattr(artwork_data, '__len__'):
            # It's already bytes
            data_to_write = artwork_data
        else:
            print(f"[extract_artwork] Unexpected artwork_data type: {type(artwork_data)}", file=sys.stderr)
            return None
        
        # Determine file extension based on artwork data
        # Try to detect format from magic bytes
        ext = 'jpg'  # Default to jpg
        if data_to_write.startswith(b'\x89PNG'):
            ext = 'png'
        elif data_to_write.startswith(b'\xff\xd8\xff'):
            ext = 'jpg'
        elif data_to_write.startswith(b'GIF'):
            ext = 'gif'
        
        # Save episode artwork
        artwork_path = os.path.join(artwork_dir, f"{base_filename}.{ext}")
        with open(artwork_path, 'wb') as f:
            f.write(data_to_write)
        
        print(f"[extract_artwork] Saved episode artwork to {artwork_path} ({len(data_to_write)} bytes)", file=sys.stderr)
        
        # Also save as channel image if channel_id is provided
        if channel_id:
            channel_artwork_path = os.path.join(artwork_dir, f"{channel_id}.{ext}")
            with open(channel_artwork_path, 'wb') as f:
                f.write(data_to_write)
            print(f"[extract_artwork] Saved channel artwork to {channel_artwork_path} ({len(data_to_write)} bytes)", file=sys.stderr)
        
        return f"/static/artwork/{base_filename}.{ext}"
    except Exception as e:
        print(f"[extract_artwork] Error saving artwork: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


@main_bp.route('/api/create-mixtape', methods=['POST'])
def create_mixtape():
    """Create a new mixtape with basic metadata"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Mixtape title is required'}), 400
    
    # Generate unique mixtape ID
    mixtape_id = generate_mixtape_id()
    
    try:
        # Create new mixtape in database
        new_mixtape = Mixtape(
            mixtape_id=mixtape_id,
            user=current_user.email,
            title=title,
            description=data.get('description', ''),
            language='en',  # Default for mixtapes
            copyright=data.get('copyright', ''),
            author=data.get('creator', ''),
            subtitle=data.get('subtitle', ''),
            summary=data.get('summary', ''),
            category=data.get('genre', ''),
            explicit=0,
            hidden=0,
            pubDate=int(datetime.utcnow().timestamp()),
            lastBuildDate=int(datetime.utcnow().timestamp())
        )
        
        db.session.add(new_mixtape)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'title': title,
            'mixtape_id': mixtape_id,
            'mixtape_url': url_for('main.mixtape_admin', mixtape_id=mixtape_id, _external=False)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating mixtape: {str(e)}'}), 500


@main_bp.route('/api/upload-track', methods=['POST'])
def upload_track():
    """Upload and extract metadata from track audio file"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        mixtape_id = request.form.get('mixtape_id')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not mixtape_id:
            return jsonify({'error': 'Mixtape ID required'}), 400
        
        # Verify mixtape exists and user has access
        mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first()
        if not mixtape:
            return jsonify({'error': 'Mixtape not found'}), 404
        
        # Check ownership: user must be admin or own the mixtape
        if not current_user.is_admin and mixtape.user != current_user.email:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Generate unique track ID
        track_id = generate_mixtape_id().replace('mt_', 'tr_')
        
        # Get file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Create static tracks directory if it doesn't exist
        tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
        os.makedirs(tracks_dir, exist_ok=True)
        
        # Save file with track ID as name
        filename = f"{track_id}{file_ext}"
        filepath = os.path.join(tracks_dir, filename)
        file.save(filepath)
        
        # Extract metadata
        metadata = extract_audio_metadata(filepath, mixtape_id, track_id)
        metadata['track_id'] = track_id
        metadata['mixtape_id'] = mixtape_id
        
        # Determine sequence number for this new track
        existing_count = Track.query.filter_by(mixtape_id=mixtape_id).count()
        sequence = existing_count + 1

        # Create track record in database
        new_track = Track(
            track_id=track_id,
            mixtape_id=mixtape_id,
            user=current_user.email,
            title=metadata.get('title', ''),
            description=metadata.get('description', ''),
            duration=metadata.get('duration', 0),
            author=metadata.get('author', ''),
            subtitle=metadata.get('subtitle', ''),
            summary=metadata.get('summary', ''),
            category=metadata.get('category', ''),
            keywords=metadata.get('keywords', ''),
            pubDate=int(datetime.utcnow().timestamp()),
            length=metadata.get('duration', 0),
            sequence=sequence
        )
        
        db.session.add(new_track)
        mixtape.lastBuildDate = int(datetime.utcnow().timestamp())
        db.session.commit()

        # Write TRCK tag and album name to the file
        total_tracks = Track.query.filter_by(mixtape_id=mixtape_id).count()
        write_trck_tag(filepath, sequence, total_tracks, album_name=mixtape.title)
        
        return jsonify({
            'success': True,
            'track_id': track_id,
            'title': metadata.get('title', 'Unknown Track'),
            'duration': metadata.get('duration', 0)
        }), 201
    except Exception as e:
        db.session.rollback()
        # Clean up the file if database insert failed
        try:
            if 'filepath' in locals():
                os.remove(filepath)
        except:
            pass
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@main_bp.route('/api/delete-track', methods=['POST'])
def delete_track():
    """Delete a track from a mixtape"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        track_id = data.get('track_id')
        
        if not track_id:
            return jsonify({'error': 'Track ID required'}), 400
        
        # Find track
        track = Track.query.filter_by(track_id=track_id).first()
        if not track:
            return jsonify({'error': 'Track not found'}), 404
        
        # Get the mixtape to verify ownership
        mixtape = Mixtape.query.filter_by(mixtape_id=track.mixtape_id).first()
        if not mixtape:
            return jsonify({'error': 'Mixtape not found'}), 404
        
        # Check ownership: user must be admin or own the mixtape
        if not current_user.is_admin and mixtape.user != current_user.email:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete associated files
        import sys
        tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
        artwork_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'artwork')
        
        for dir_path in [tracks_dir, artwork_dir]:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.startswith(track_id):
                        try:
                            file_path = os.path.join(dir_path, filename)
                            os.remove(file_path)
                            print(f"[delete_track] Deleted {file_path}", file=sys.stderr)
                        except Exception as e:
                            print(f"[delete_track] Error deleting file: {e}", file=sys.stderr)
        
        # Delete database record
        mixtape.lastBuildDate = int(datetime.utcnow().timestamp())
        db.session.delete(track)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Track deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error deleting track: {str(e)}'}), 500


@main_bp.route('/mixtape-style/<mixtape_id>')
def mixtape_style(mixtape_id):
    """Style customization page for a mixtape"""
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first_or_404()
    return render_template('mixtape_style.html', user=current_user, mixtape=mixtape)


@main_bp.route('/api/get-mixtape-style/<mixtape_id>', methods=['GET'])
def get_mixtape_style(mixtape_id):
    """Get style settings for a mixtape"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first()
    if not mixtape:
        return jsonify({'error': 'Mixtape not found'}), 404
    
    return jsonify({
        'style': {
            'shell_color': mixtape.style_shell_color or '#ff9100',
            'shell_opacity': mixtape.style_shell_opacity or 0.3,
            'reel_color': mixtape.style_reel_color or '#ff9100',
            'reel_opacity': mixtape.style_reel_opacity or 1.0,
            'clip_color': mixtape.style_clip_color or '#ff9100',
            'clip_opacity': mixtape.style_clip_opacity or 1.0,
            'guide_color': mixtape.style_guide_color or '#8e8e8e',
            'guide_opacity': mixtape.style_guide_opacity or 1.0,
            'label_color': mixtape.style_label_color or '#ffffff',
            'label_opacity': mixtape.style_label_opacity or 1.0,
            'meter_color': mixtape.style_meter_color or '#ff9100',
            'meter_opacity': mixtape.style_meter_opacity or 0.3,
            'screw_color': mixtape.style_screw_color or '#8e8e8e',
            'screw_star_opacity': mixtape.style_screw_star_opacity or 0.3,
            'label_display_mode': mixtape.label_display_mode or 'Top and Bottom Labels',
            'label_font_family': mixtape.label_font_family or 'Arial',
            'label_upper_text': mixtape.label_upper_text or '',
            'label_upper_font_size': mixtape.label_upper_font_size or 12,
            'label_upper_opacity': mixtape.label_upper_opacity if mixtape.label_upper_opacity is not None else 1.0,
            'label_lower_text': mixtape.label_lower_text or '',
            'label_lower_font_size': mixtape.label_lower_font_size or 10,
            'label_lower_opacity': mixtape.label_lower_opacity if mixtape.label_lower_opacity is not None else 1.0,
            'overlay_filename': mixtape.overlay_filename or ''
        }
    })


@main_bp.route('/api/save-mixtape-style/<mixtape_id>', methods=['POST'])
def save_mixtape_style(mixtape_id):
    """Save style customization for a mixtape"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403
    
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first()
    if not mixtape:
        return jsonify({'error': 'Mixtape not found'}), 404
    
    # Check ownership: user must be admin or own the mixtape
    if not current_user.is_admin and mixtape.user != current_user.email:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Update style fields
        mixtape.style_shell_color = data.get('shell_color', '#ff9100')
        mixtape.style_shell_opacity = float(data.get('shell_opacity', 0.3))
        mixtape.style_reel_color = data.get('reel_color', '#ff9100')
        mixtape.style_reel_opacity = float(data.get('reel_opacity', 1.0))
        mixtape.style_clip_color = data.get('clip_color', '#ff9100')
        mixtape.style_clip_opacity = float(data.get('clip_opacity', 1.0))
        mixtape.style_guide_color = data.get('guide_color', '#8e8e8e')
        mixtape.style_guide_opacity = float(data.get('guide_opacity', 1.0))
        mixtape.style_label_color = data.get('label_color', '#ffffff')
        mixtape.style_label_opacity = float(data.get('label_opacity', 1.0))
        mixtape.style_meter_color = data.get('meter_color', '#ff9100')
        mixtape.style_meter_opacity = float(data.get('meter_opacity', 0.3))
        mixtape.style_screw_color = data.get('screw_color', '#8e8e8e')
        mixtape.style_screw_star_opacity = float(data.get('screw_star_opacity', 0.3))
        
        # Update label display mode
        mixtape.label_display_mode = data.get('label_display_mode', 'Top and Bottom Labels')
        
        # Update label text and font
        mixtape.label_font_family = data.get('label_font_family', 'Arial')
        mixtape.label_upper_text = data.get('label_upper_text', '')
        mixtape.label_upper_font_size = int(data.get('label_upper_font_size', 12))
        mixtape.label_upper_opacity = float(data.get('label_upper_opacity', 1.0))
        mixtape.label_lower_text = data.get('label_lower_text', '')
        mixtape.label_lower_font_size = int(data.get('label_lower_font_size', 10))
        mixtape.label_lower_opacity = float(data.get('label_lower_opacity', 1.0))
        mixtape.overlay_filename = data.get('overlay_filename', None)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Style saved successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error saving style: {str(e)}'}), 500


@main_bp.route('/api/get-overlay-files', methods=['GET'])
def get_overlay_files():
    """Get list of available overlay PNG files"""
    overlay_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'overlays')
    overlays = []
    
    if os.path.exists(overlay_dir):
        for filename in os.listdir(overlay_dir):
            if filename.lower().endswith('.png'):
                overlays.append(filename)
    
    return jsonify({'overlays': sorted(overlays)})


def format_date_with_ordinal(date_obj):
    """Format date as 'Monday, January 5th, 2026'"""
    day = date_obj.day
    month = date_obj.strftime('%B')
    weekday = date_obj.strftime('%A')
    year = date_obj.year
    
    # Determine ordinal suffix
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    return f"{weekday}, {month} {day}{suffix}, {year}"


@main_bp.route('/mixtape/<mixtape_id>/m3u')
def mixtape_m3u(mixtape_id):
    """Generate M3U playlist for a mixtape"""
    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first_or_404()
    tracks = Track.query.filter_by(mixtape_id=mixtape_id).order_by(Track.sequence.asc(), Track.pubDate.asc()).all()
    
    # Build M3U content
    m3u_lines = ['#EXTM3U']
    m3u_lines.append(f'#PLAYLIST:{mixtape.title}')
    
    for track in tracks:
        # Try to find the audio file
        tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
        file_url = None
        duration = track.duration or 0
        
        # Search for file matching track_id ID
        if os.path.exists(tracks_dir):
            for filename in os.listdir(tracks_dir):
                if filename.startswith(track.track_id):
                    file_path = os.path.join(tracks_dir, filename)
                    try:
                        # Get file URL
                        file_url = f"{request.host_url.rstrip('/')}/static/tracks/{filename}"
                    except:
                        pass
                    break
        
        if file_url:
            # Add track info in M3U format with artist
            title_part = track.title or 'Unknown Track'
            if track.author:
                track_info = f"#EXTINF:{duration},{track.author} - {title_part}"
            else:
                track_info = f"#EXTINF:{duration},{title_part}"
            m3u_lines.append(track_info)
            m3u_lines.append(file_url)
    
    # Create M3U content
    m3u_content = '\n'.join(m3u_lines)
    
    # Return with proper M3U content type
    return Response(m3u_content, mimetype='audio/x-mpegurl', 
                   headers={"Content-Disposition": f'attachment; filename="{mixtape.title}.m3u"'})


@main_bp.route('/mixtape/<mixtape_id>/zip')
def mixtape_zip(mixtape_id):
    """Download all tracks for a mixtape as a ZIP archive"""
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))

    import zipfile
    import re

    mixtape = Mixtape.query.filter_by(mixtape_id=mixtape_id).first_or_404()
    tracks = Track.query.filter_by(mixtape_id=mixtape_id).order_by(Track.sequence.asc(), Track.pubDate.asc()).all()

    tracks_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'tracks')
    zips_dir = os.path.join(current_app.config['DOCROOT'], 'app/static', 'zips')
    os.makedirs(zips_dir, exist_ok=True)

    zip_filename = f"{mixtape_id}.zip"
    zip_path = os.path.join(zips_dir, zip_filename)

    # Rebuild ZIP if missing or older than the last playlist update
    needs_rebuild = True
    if os.path.exists(zip_path) and mixtape.lastBuildDate:
        if os.path.getmtime(zip_path) >= mixtape.lastBuildDate:
            needs_rebuild = False

    if needs_rebuild:
        def arc_safe(name):
            return re.sub(r'[/\\:*?"<>|]', '_', name or '').strip()

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
            for i, track in enumerate(tracks):
                if not os.path.exists(tracks_dir):
                    continue
                for filename in os.listdir(tracks_dir):
                    if filename.startswith(track.track_id):
                        ext = os.path.splitext(filename)[1]
                        parts = [f"{i + 1:02d}"]
                        if track.author:
                            parts.append(arc_safe(track.author))
                        parts.append(arc_safe(track.title or track.track_id))
                        arc_name = ' - '.join(parts) + ext
                        zf.write(os.path.join(tracks_dir, filename), arc_name)
                        break

    safe_title = secure_filename(mixtape.title or mixtape_id)
    return send_from_directory(zips_dir, zip_filename, as_attachment=True,
                               download_name=f"{safe_title}.zip")
