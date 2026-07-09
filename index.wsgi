import sys
import os
import site
import glob
import traceback

LOG_FILE = '/tmp/podcast_wsgi_error.log'

def log(msg):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{msg}\n")
    except Exception as e:
        pass

try:
    log(f"\n[WSGI] ========== Starting WSGI initialization ==========")
    log(f"[WSGI] Python version: {sys.version}")
    log(f"[WSGI] sys.executable: {sys.executable}")
    
    # Resolve project root relative to this file
    project_home = os.path.dirname(os.path.abspath(__file__))
    log(f"[WSGI] project_home: {project_home}")
    
    venv_path = os.path.join(project_home, 'geo')
    log(f"[WSGI] venv_path: {venv_path}")
    log(f"[WSGI] venv exists: {os.path.exists(venv_path)}")
    
    # Ensure project is in path
    sys.path.insert(0, project_home)
    
    # Dynamically find and add site-packages from venv
    site_packages_patterns = glob.glob(os.path.join(venv_path, 'lib', 'python*', 'site-packages'))
    log(f"[WSGI] site_packages_patterns: {site_packages_patterns}")
    
    if site_packages_patterns:
        site_packages_path = site_packages_patterns[0]
        log(f"[WSGI] Using site_packages: {site_packages_path}")
        site.addsitedir(site_packages_path)
        sys.path.insert(0, site_packages_path)
    else:
        log(f"[WSGI] WARNING: No site-packages found in venv")
    
    # Activate the virtual environment
    activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
    if os.path.exists(activate_this):
        log(f"[WSGI] Activating venv with {activate_this}")
        with open(activate_this) as f:
            exec(f.read(), {'__file__': activate_this})
        log(f"[WSGI] Venv activated successfully")
    else:
        log(f"[WSGI] WARNING: activate_this.py not found at {activate_this}")
    
    # Load environment variables from .env file
    log(f"[WSGI] Loading .env file...")
    from dotenv import load_dotenv
    
    env_path = os.path.join(project_home, '.env')
    log(f"[WSGI] env_path: {env_path}")
    log(f"[WSGI] env_path exists: {os.path.exists(env_path)}")
    
    loaded = load_dotenv(env_path)
    log(f"[WSGI] load_dotenv returned: {loaded}")
    log(f"[WSGI] FLASK_ENV: {os.getenv('FLASK_ENV')}")
    log(f"[WSGI] DATABASE_URL: {os.getenv('DATABASE_URL')}")
    log(f"[WSGI] DEV_DATABASE_URL: {os.getenv('DEV_DATABASE_URL')}")
    
    # Import and run the application
    log(f"[WSGI] Importing Flask and create_app...")
    import flask
    log(f"[WSGI] Flask loaded from: {flask.__file__}")
    log(f"[WSGI] Flask version: {flask.__version__}")
    
    from app import create_app
    log(f"[WSGI] create_app imported successfully")
    
    # Use the FLASK_ENV from .env, default to development
    flask_env = os.getenv('FLASK_ENV', 'development')
    log(f"[WSGI] Creating app with FLASK_ENV={flask_env}")
    
    application = create_app(flask_env)
    log(f"[WSGI] Application created successfully!")
    log(f"[WSGI] ========== WSGI initialization complete ==========\n")

except Exception as e:
    log(f"[WSGI] ERROR during initialization: {str(e)}")
    log(f"[WSGI] Traceback:\n{traceback.format_exc()}")
    
    # Create a fallback WSGI app that returns the error
    def application(environ, start_response):
        status = '500 Internal Server Error'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        error_msg = f"WSGI initialization failed. Check {LOG_FILE} for details.\n\nError: {str(e)}\n\n{traceback.format_exc()}"
        return [error_msg.encode('utf-8')]
        f.write(traceback.format_exc())
    raise
