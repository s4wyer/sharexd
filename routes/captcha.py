from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
import time
import secrets
import random
import re
from extensions import limiter, meta_db

captcha_bp = Blueprint('captcha', __name__)

@captcha_bp.route('/view/<path:path>/verify', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def verify_captcha(path):
    safe_path = secure_filename(path)

    current_time = time.time()

    if request.method == 'GET':
        if 'euler' in request.args:
            captcha_type = 'rhythm'
        elif 'sql' in request.args:
            captcha_type = 'sql'
        elif 'slider' in request.args:
            captcha_type = 'slider'
        elif 'regex' in request.args:
            captcha_type = 'regex'
        else:
            captcha_type = random.choice(['rhythm', 'sql', 'slider', 'regex'])
        
        challenge_id = secrets.token_hex(8)
        meta_db.set(f"captcha_{challenge_id}", {'time': time.time(), 'type': captcha_type})
        
        if captcha_type == 'rhythm':
            return render_template('verify_rhythm.html', filename=safe_path, challenge_id=challenge_id)
        elif captcha_type == 'sql':
            return render_template('verify_sql.html', filename=safe_path, challenge_id=challenge_id)
        elif captcha_type == 'slider':
            return render_template('verify_slider.html', filename=safe_path, challenge_id=challenge_id)
        elif captcha_type == 'regex':
            return render_template('verify_regex.html', filename=safe_path, challenge_id=challenge_id, regex_pattern=r'^sxd-(BEEP|BOOP)-[A-Z]{3,5}(?<!Q)-[13579]{2,4}-[^a-zA-Z0-9\s]{2}-(MOO|MEOW|QUACK)-\1-\2-[a-z0-9]{4}-TOTALLY_HUMAN$')
        
        return jsonify({"error": "Unknown captcha type."}), 400

    elif request.method == 'POST':
        challenge_id = request.form.get('challenge_id')
        challenge_data = meta_db.get(f"captcha_{challenge_id}") if challenge_id else None
        if challenge_id:
            meta_db.delete(f"captcha_{challenge_id}")
        
        if not challenge_data or current_time - (challenge_data.get('time', 0) if isinstance(challenge_data, dict) else challenge_data) > 300:
            new_challenge = secrets.token_hex(8)
            meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'rhythm'})
            return render_template('verify_rhythm.html', filename=safe_path, challenge_id=new_challenge, error="Session expired. Try again.")
            
        if not isinstance(challenge_data, dict):
            start_time = challenge_data
            captcha_type = 'rhythm'
        else:
            start_time = challenge_data['time']
            captcha_type = challenge_data['type']
            
        if captcha_type == 'rhythm':
            server_elapsed = time.time() - start_time
            client_elapsed_str = request.form.get('client_elapsed', '')
            try:
                client_elapsed = float(client_elapsed_str) / 1000.0
            except ValueError:
                client_elapsed = server_elapsed
                
            elapsed = client_elapsed
            target = 2.718
            tolerance = 0.1
            
            if server_elapsed < target - 0.5:
                new_challenge = secrets.token_hex(8)
                meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'rhythm'})
                return render_template('verify_rhythm.html', filename=safe_path, challenge_id=new_challenge,
                                       error="Rejected for time manipulation.")
            
            if abs(elapsed - target) <= tolerance:
                session[f'verified_{safe_path}'] = True
                return redirect(url_for('files.view_file', path=safe_path))
            else:
                new_challenge = secrets.token_hex(8)
                meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'rhythm'})
                return render_template('verify_rhythm.html', filename=safe_path, challenge_id=new_challenge,
                                       error=f"Rejected for being out of rhythm. You took {elapsed:.3f}s. We needed exactly 2.718s.")
                                       
        elif captcha_type == 'sql':
            token = request.form.get('token', '')
            
            is_bypass = False
            if "'" in token or '"' in token:
                token_lower = token.lower()
                if "or" in token_lower or "=" in token_lower or "--" in token_lower or "#" in token_lower:
                    is_bypass = True

            if is_bypass:
                session[f'verified_{safe_path}'] = True
                return redirect(url_for('files.view_file', path=safe_path))
            else:
                new_challenge = secrets.token_hex(8)
                meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'sql'})
                
                fake_query = f"SELECT * FROM access_tokens WHERE token = '{token}'"
                error_msg = f"ERR: 0 rows returned for query: {fake_query}"
                return render_template('verify_sql.html', filename=safe_path, challenge_id=new_challenge,
                                       error=error_msg)
                                       
        elif captcha_type == 'slider':
            slider_value_str = request.form.get('slider_value', '')
            try:
                slider_value = float(slider_value_str)
            except ValueError:
                slider_value = 0.0
                
            if abs(slider_value - 42.0) < 0.00001:
                session[f'verified_{safe_path}'] = True
                return redirect(url_for('files.view_file', path=safe_path))
            else:
                new_challenge = secrets.token_hex(8)
                meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'slider'})
                return render_template('verify_slider.html', filename=safe_path, challenge_id=new_challenge,
                                       error=f"Rejected. You dragged to {slider_value:.4f}%. We needed exactly 42.0000%.")
                                       
        elif captcha_type == 'regex':
            token = request.form.get('token', '')
            pattern = r'^sxd-(BEEP|BOOP)-[A-Z]{3,5}(?<!Q)-[13579]{2,4}-[^a-zA-Z0-9\s]{2}-(MOO|MEOW|QUACK)-\1-\2-[a-z0-9]{4}-TOTALLY_HUMAN$'
            if re.match(pattern, token):
                session[f'verified_{safe_path}'] = True
                return redirect(url_for('files.view_file', path=safe_path))
            else:
                new_challenge = secrets.token_hex(8)
                meta_db.set(f"captcha_{new_challenge}", {'time': time.time(), 'type': 'regex'})
                return render_template('verify_regex.html', filename=safe_path, challenge_id=new_challenge,
                                       regex_pattern=pattern,
                                       error="Rejected. The string did not match the required pattern.")
                
        return jsonify({"error": "Unknown captcha type."}), 400
