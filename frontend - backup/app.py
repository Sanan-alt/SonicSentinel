import os
import uuid
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sonicsentinel-secret-key-2026-acoustic-ai')

# ==========================================
# 10 MANDATORY SOUND CATEGORIES
# ==========================================
MANDATORY_SOUND_CATEGORIES = [
    {
        "id": "cat_1",
        "name": "Machinery Fault",
        "category_key": "machinery_fault",
        "severity": "Warning",
        "badge_color": "warning",
        "icon": "fa-gears",
        "description": "Bearing wear, motor friction, turbine imbalance, or mechanical vibrations",
        "default_threshold": 0.70
    },
    {
        "id": "cat_2",
        "name": "Glass Breaking",
        "category_key": "glass_breaking",
        "severity": "Critical",
        "badge_color": "danger",
        "icon": "fa-burst",
        "description": "Sharp high-frequency shattering of window, door, or structural glass",
        "default_threshold": 0.85
    },
    {
        "id": "cat_3",
        "name": "Alarm or Siren",
        "category_key": "alarm_siren",
        "severity": "Warning",
        "badge_color": "warning",
        "icon": "fa-bell",
        "description": "Continuous or oscillating sirens, fire alarms, evacuation alerts",
        "default_threshold": 0.80
    },
    {
        "id": "cat_4",
        "name": "Vehicle Horn",
        "category_key": "vehicle_horn",
        "severity": "Moderate",
        "badge_color": "info",
        "icon": "fa-bullhorn",
        "description": "Automotive blare, sustained klaxon or proximity honks",
        "default_threshold": 0.75
    },
    {
        "id": "cat_5",
        "name": "Animal Sound",
        "category_key": "animal_sound",
        "severity": "Low",
        "badge_color": "neutral",
        "icon": "fa-paw",
        "description": "Aggressive canine barking, perimeter distress, or wildlife intrusion",
        "default_threshold": 0.65
    },
    {
        "id": "cat_6",
        "name": "Gunshot",
        "category_key": "gunshot",
        "severity": "Critical",
        "badge_color": "danger",
        "icon": "fa-crosshairs",
        "description": "High-decibel muzzle blast and supersonic ballistic crack",
        "default_threshold": 0.90
    },
    {
        "id": "cat_7",
        "name": "Panic Scream",
        "category_key": "panic_scream",
        "severity": "Critical",
        "badge_color": "danger",
        "icon": "fa-person-falling-burst",
        "description": "High-pitch human distress shrieks, screams of fear or severe pain",
        "default_threshold": 0.82
    },
    {
        "id": "cat_8",
        "name": "Aggression or Violent Conflict",
        "category_key": "aggression_conflict",
        "severity": "Critical",
        "badge_color": "danger",
        "icon": "fa-hand-fist",
        "description": "Verbal hostility, elevated screaming fights, physical altercation impacts",
        "default_threshold": 0.78
    },
    {
        "id": "cat_9",
        "name": "Person Asking for Help",
        "category_key": "person_help",
        "severity": "Critical",
        "badge_color": "danger",
        "icon": "fa-handshake-angle",
        "description": "Vocal distress cues ('Help', 'Call Police', 'Bachao', emergency pleas)",
        "default_threshold": 0.75
    },
    {
        "id": "cat_10",
        "name": "Background Noise",
        "category_key": "background_noise",
        "severity": "Ambient",
        "badge_color": "secondary",
        "icon": "fa-wave-square",
        "description": "Normal ambient traffic, wind, ventilation, footsteps or stationary hum",
        "default_threshold": 0.50
    }
]

# ==========================================
# USER ROLES
# ==========================================
USER_ROLES = [
    "Normal user",
    "Audio reviewer",
    "Security operator",
    "Maintenance operator",
    "Administrator"
]

# In-memory users for demonstration (with default demo accounts)
USERS_DB = {
    "admin@sonicsentinel.ai": {
        "id": "SS-USR-10001",
        "name": "Commander Sarah Vance",
        "email": "admin@sonicsentinel.ai",
        "password": "admin",
        "role": "Administrator",
        "department": "Acoustic Threat Operations",
        "created_at": "2026-01-10"
    },
    "operator@sonicsentinel.ai": {
        "id": "SS-USR-10002",
        "name": "Officer Tariq Malik",
        "email": "operator@sonicsentinel.ai",
        "password": "operator",
        "role": "Security operator",
        "department": "Rapid Response Unit",
        "created_at": "2026-02-14"
    },
    "reviewer@sonicsentinel.ai": {
        "id": "SS-USR-10003",
        "name": "Dr. Aisha Khan",
        "email": "reviewer@sonicsentinel.ai",
        "password": "reviewer",
        "role": "Audio reviewer",
        "department": "Forensic Audio Analytics",
        "created_at": "2026-03-01"
    }
}

# Sample live event data using the 10 mandatory categories
SAMPLE_EVENTS = [
    {
        "id": "EVT-8921",
        "category": "Panic Scream",
        "category_key": "panic_scream",
        "severity": "Critical",
        "confidence_py": 94.2,
        "confidence_tm": 91.5,
        "location": "North Transit Hub - Sector 4",
        "timestamp": "Just now",
        "duration": "1.8s",
        "snr_db": 24.5,
        "status": "Verified",
        "sample_type": "scream"
    },
    {
        "id": "EVT-8920",
        "category": "Gunshot",
        "category_key": "gunshot",
        "severity": "Critical",
        "confidence_py": 97.8,
        "confidence_tm": 95.1,
        "location": "West Perimeter Gate 3",
        "timestamp": "2 min ago",
        "duration": "0.7s",
        "snr_db": 31.2,
        "status": "Flagged",
        "sample_type": "gunshot"
    },
    {
        "id": "EVT-8919",
        "category": "Glass Breaking",
        "category_key": "glass_breaking",
        "severity": "Critical",
        "confidence_py": 88.4,
        "confidence_tm": 86.0,
        "location": "Commercial Plaza East - Storefront B",
        "timestamp": "9 min ago",
        "duration": "1.2s",
        "snr_db": 19.8,
        "status": "Investigating",
        "sample_type": "glass"
    },
    {
        "id": "EVT-8918",
        "category": "Aggression or Violent Conflict",
        "category_key": "aggression_conflict",
        "severity": "Critical",
        "confidence_py": 86.1,
        "confidence_tm": 83.7,
        "location": "Central Parking Level -2",
        "timestamp": "18 min ago",
        "duration": "3.4s",
        "snr_db": 18.2,
        "status": "Resolved",
        "sample_type": "aggression"
    },
    {
        "id": "EVT-8917",
        "category": "Machinery Fault",
        "category_key": "machinery_fault",
        "severity": "Warning",
        "confidence_py": 82.5,
        "confidence_tm": 79.0,
        "location": "Generator Substation 09",
        "timestamp": "34 min ago",
        "duration": "5.0s",
        "snr_db": 15.6,
        "status": "Review Pending",
        "sample_type": "machinery"
    },
    {
        "id": "EVT-8916",
        "category": "Alarm or Siren",
        "category_key": "alarm_siren",
        "severity": "Warning",
        "confidence_py": 95.0,
        "confidence_tm": 96.2,
        "location": "Industrial Depot C",
        "timestamp": "1 hr ago",
        "duration": "8.5s",
        "snr_db": 26.4,
        "status": "Verified",
        "sample_type": "siren"
    },
    {
        "id": "EVT-8915",
        "category": "Person Asking for Help",
        "category_key": "person_help",
        "severity": "Critical",
        "confidence_py": 89.0,
        "confidence_tm": 85.5,
        "location": "South Stairwell Level 3",
        "timestamp": "2 hrs ago",
        "duration": "2.1s",
        "snr_db": 21.0,
        "status": "Verified",
        "sample_type": "help"
    },
    {
        "id": "EVT-8914",
        "category": "Vehicle Horn",
        "category_key": "vehicle_horn",
        "severity": "Moderate",
        "confidence_py": 78.4,
        "confidence_tm": 75.1,
        "location": "Main Entrance Barrier",
        "timestamp": "3 hrs ago",
        "duration": "2.0s",
        "snr_db": 17.5,
        "status": "Resolved",
        "sample_type": "horn"
    },
    {
        "id": "EVT-8913",
        "category": "Animal Sound",
        "category_key": "animal_sound",
        "severity": "Low",
        "confidence_py": 72.0,
        "confidence_tm": 70.4,
        "location": "Perimeter Fence North",
        "timestamp": "4 hrs ago",
        "duration": "1.5s",
        "snr_db": 12.8,
        "status": "Resolved",
        "sample_type": "animal"
    },
    {
        "id": "EVT-8912",
        "category": "Background Noise",
        "category_key": "background_noise",
        "severity": "Ambient",
        "confidence_py": 99.1,
        "confidence_tm": 98.4,
        "location": "All Zones Baseline",
        "timestamp": "5 hrs ago",
        "duration": "10.0s",
        "snr_db": 6.2,
        "status": "Baseline",
        "sample_type": "noise"
    }
]

# Helper context processor so every template has active user & categories
@app.context_processor
def inject_global_data():
    current_user = session.get('user')
    return {
        'current_user': current_user,
        'sound_categories': MANDATORY_SOUND_CATEGORIES,
        'user_roles': USER_ROLES,
        'active_units_online': 1482
    }

# ==========================================
# ROUTES
# ==========================================

# 1. Landing Page (Ref: soundeventdetector.eu style hero + digital wave animation)
@app.route('/')
def index():
    return render_template('index.html', recent_events=SAMPLE_EVENTS[:4])

# 2. Authentication: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        user = USERS_DB.get(email)
        if user and user['password'] == password:
            session['user'] = {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'role': user['role'],
                'department': user.get('department', 'General Security')
            }
            flash(f"Welcome back, {user['name']}! Logged in as {user['role']}.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. You can use demo accounts below.", "danger")
            
    return render_template('login.html')

# 3. Authentication: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'Normal user')
        department = request.form.get('department', 'Acoustic Monitoring')
        
        if not name or not email or not password:
            flash("Please fill in all required fields.", "warning")
            return render_template('register.html')
            
        if email in USERS_DB:
            flash("An account with this email already exists. Please login.", "info")
            return redirect(url_for('login'))
            
        # Assign unique User ID format: SS-USR-XXXXX
        unique_id = f"SS-USR-{uuid.uuid4().hex[:5].upper()}"
        
        new_user = {
            "id": unique_id,
            "name": name,
            "email": email,
            "password": password,
            "role": role,
            "department": department,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        USERS_DB[email] = new_user
        
        session['user'] = {
            'id': new_user['id'],
            'name': new_user['name'],
            'email': new_user['email'],
            'role': new_user['role'],
            'department': new_user['department']
        }
        
        flash(f"Registration successful! Your Unique ID is {unique_id}.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

# 4. Authentication: Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been securely signed out.", "info")
    return redirect(url_for('index'))

# 5. User Profile Management
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('user'):
        flash("Please log in to manage your profile.", "warning")
        return redirect(url_for('login'))
        
    user = session['user']
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        role = request.form.get('role', user['role'])
        
        user['name'] = name or user['name']
        user['department'] = department or user['department']
        user['role'] = role
        session['user'] = user
        
        # update DB
        if user['email'] in USERS_DB:
            USERS_DB[user['email']]['name'] = user['name']
            USERS_DB[user['email']]['department'] = user['department']
            USERS_DB[user['email']]['role'] = user['role']
            
        flash("Profile updated successfully.", "success")
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=user)

# 6. Main Operations Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', events=SAMPLE_EVENTS)

# 7. Live Microphone Monitoring
@app.route('/live-monitor')
def live_monitor():
    return render_template('live_monitor.html')

# 8. Uploaded Audio Analysis (Single & Batch Upload + Dual Model Comparison)
@app.route('/audio-analysis')
def audio_analysis():
    return render_template('audio_analysis.html')

# 9. Critical Event Detection & Alerts Center
@app.route('/critical-events')
def critical_events():
    critical_list = [e for e in SAMPLE_EVENTS if e['severity'] == 'Critical']
    return render_template('critical_events.html', events=critical_list)

# 10. Manual Review & Verification Workflow
@app.route('/manual-review')
def manual_review():
    review_queue = [e for e in SAMPLE_EVENTS if e['status'] in ['Flagged', 'Review Pending', 'Investigating']]
    return render_template('manual_review.html', events=review_queue)

# 11. Event History & Audit Log
@app.route('/event-history')
def event_history():
    return render_template('event_history.html', events=SAMPLE_EVENTS)

# 12. Dashboard Reports & Export
@app.route('/reports')
def reports():
    return render_template('reports.html', events=SAMPLE_EVENTS)

# 13. About Us & Technology Architecture
@app.route('/about')
def about():
    return render_template('about.html')

# ==========================================
# API ENDPOINTS (For Audio validation, inference simulation, & Live status)
# ==========================================

# API: Audio File Validation (Format, Size, Duration, Sampling Rate)
@app.route('/api/validate-audio', methods=['POST'])
def validate_audio():
    # Support validation data received from client
    data = request.json or {}
    filename = data.get('filename', '')
    size_bytes = data.get('size_bytes', 0)
    duration_sec = data.get('duration_sec', 0)
    sample_rate = data.get('sample_rate', 44100)
    
    allowed_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    ext = os.path.splitext(filename.lower())[1]
    
    errors = []
    if ext not in allowed_extensions:
        errors.append(f"Invalid format '{ext}'. Allowed formats: WAV, MP3, FLAC, OGG, M4A.")
        
    # Max size 25MB
    if size_bytes > 25 * 1024 * 1024:
        errors.append(f"File size exceeds 25MB limit ({size_bytes / (1024*1024):.2f}MB).")
        
    # Max duration 180s (3 minutes)
    if duration_sec > 180:
        errors.append(f"Audio duration exceeds 180 seconds ({duration_sec:.1f}s).")
        
    is_valid = len(errors) == 0
    return jsonify({
        "valid": is_valid,
        "format": ext.upper().replace('.', ''),
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_sec": round(duration_sec, 2),
        "sample_rate_hz": sample_rate,
        "errors": errors
    })

# API: Dual Model Audio Classification (Python Sound Model vs Google Teachable Machine)
@app.route('/api/classify-audio', methods=['POST'])
def classify_audio():
    import random
    data = request.json or {}
    sound_type = data.get('sound_type', '')
    
    # Pick target category from 10 mandatory categories
    matched = None
    if sound_type:
        for cat in MANDATORY_SOUND_CATEGORIES:
            if cat['category_key'] == sound_type or cat['name'].lower() == sound_type.lower():
                matched = cat
                break
                
    if not matched:
        # Default or pick one of critical/mandatory
        matched = random.choice(MANDATORY_SOUND_CATEGORIES[:4])
        
    # Generate realistic dual-model prediction scores
    py_confidence = round(random.uniform(85.0, 98.5), 1)
    # Teachable machine slight variance (+/- 3-5%)
    tm_confidence = round(max(50.0, min(99.0, py_confidence + random.uniform(-4.5, 3.5))), 1)
    
    snr = round(random.uniform(18.0, 32.5), 1)
    clipping_ratio = round(random.uniform(0.0, 2.5), 2)
    background_noise_level = round(random.uniform(25.0, 48.0), 1)
    
    # Check if critical event
    is_critical = matched['severity'] == 'Critical'
    
    return jsonify({
        "event_id": f"EVT-{random.randint(1000, 9999)}",
        "category_name": matched['name'],
        "category_key": matched['category_key'],
        "severity": matched['severity'],
        "is_critical": is_critical,
        "python_model": {
            "name": "SonicNet-V4 Acoustic ResNet",
            "confidence": py_confidence,
            "threshold": matched['default_threshold'] * 100
        },
        "teachable_machine": {
            "name": "Google Teachable Machine (Audio V2)",
            "confidence": tm_confidence,
            "threshold": matched['default_threshold'] * 100
        },
        "confidence_delta": round(abs(py_confidence - tm_confidence), 1),
        "audio_quality": {
            "snr_db": snr,
            "clipping_percent": clipping_ratio,
            "background_noise_db": background_noise_level,
            "quality_rating": "Optimal" if snr > 20 and clipping_ratio < 1 else "Moderate"
        },
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d")
    })

if __name__ == '__main__':
    print("Starting SonicSentinel AI Acoustic Threat Detection Server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
