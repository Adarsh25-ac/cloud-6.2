import os
import time
import socket
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cloud-practical-secret-key-2026')

# Database configuration from Environment Variables
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 5432))
DB_NAME = os.environ.get('DB_NAME', 'recipedb')
DB_USER = os.environ.get('DB_USER', 'recipeuser')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'recipepassword')

def get_local_ip():
    """Retrieve the host/container internal IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_db_connection(max_retries=5, delay=2):
    """Establishes database connection with automatic retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )
            return conn
        except Exception as e:
            print(f"[DB Retry {attempt}/{max_retries}] Connecting to {DB_HOST}:{DB_PORT} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                raise e

def init_tables_if_needed():
    """Ensure the table exists in case the DB container was initialized without init.sql."""
    try:
        conn = get_db_connection(max_retries=2, delay=1)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    prep_time INTEGER NOT NULL,
                    cook_time INTEGER NOT NULL,
                    servings INTEGER NOT NULL DEFAULT 2,
                    ingredients TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    image_url VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Initial DB table verification failed: {e}")

# Context processor to pass network/system metadata to all templates
@app.context_processor
def inject_metadata():
    return {
        'db_host': DB_HOST,
        'db_port': DB_PORT,
        'db_name': DB_NAME,
        'app_ip': get_local_ip()
    }

@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    
    db_connected = True
    error_msg = None
    recipes = []
    
    try:
        conn = get_db_connection(max_retries=2, delay=1)
        with conn.cursor() as cur:
            query = "SELECT * FROM recipes WHERE 1=1"
            params = []
            
            if search_query:
                query += " AND (title ILIKE %s OR ingredients ILIKE %s)"
                params.extend([f"%{search_query}%", f"%{search_query}%"])
            
            if category_filter:
                query += " AND category = %s"
                params.append(category_filter)
                
            query += " ORDER BY id DESC"
            cur.execute(query, tuple(params))
            recipes = cur.fetchall()
            
            # Fetch distinct categories for filter buttons
            cur.execute("SELECT DISTINCT category FROM recipes ORDER BY category")
            categories = [row['category'] for row in cur.fetchall()]
            
        conn.close()
    except Exception as e:
        db_connected = False
        error_msg = str(e)
        categories = []

    return render_template(
        'index.html',
        recipes=recipes,
        categories=categories,
        search_query=search_query,
        selected_category=category_filter,
        db_connected=db_connected,
        error_msg=error_msg
    )

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
            recipe = cur.fetchone()
        conn.close()
        
        if not recipe:
            flash("Recipe not found.", "danger")
            return redirect(url_for('index'))
            
        return render_template('recipe_detail.html', recipe=recipe)
    except Exception as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_recipe():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        prep_time = request.form.get('prep_time', '0').strip()
        cook_time = request.form.get('cook_time', '0').strip()
        servings = request.form.get('servings', '2').strip()
        ingredients = request.form.get('ingredients', '').strip()
        instructions = request.form.get('instructions', '').strip()
        image_url = request.form.get('image_url', '').strip()
        
        if not title or not ingredients or not instructions:
            flash("Please fill in all required fields (Title, Ingredients, Instructions).", "warning")
            return render_template('add_recipe.html')
            
        if not image_url:
            image_url = "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=600&q=80"
            
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO recipes (title, category, prep_time, cook_time, servings, ingredients, instructions, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    title,
                    category or 'General',
                    int(prep_time) if prep_time.isdigit() else 0,
                    int(cook_time) if cook_time.isdigit() else 0,
                    int(servings) if servings.isdigit() else 2,
                    ingredients,
                    instructions,
                    image_url
                ))
                new_id = cur.fetchone()['id']
                conn.commit()
            conn.close()
            flash(f"Recipe '{title}' added successfully!", "success")
            return redirect(url_for('recipe_detail', recipe_id=new_id))
        except Exception as e:
            flash(f"Failed to add recipe: {e}", "danger")
            return render_template('add_recipe.html')

    return render_template('add_recipe.html')

@app.route('/delete/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
            conn.commit()
        conn.close()
        flash("Recipe deleted successfully.", "info")
    except Exception as e:
        flash(f"Error deleting recipe: {e}", "danger")
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check endpoint to test VM1 to VM2 connectivity."""
    db_status = "healthy"
    latency_ms = None
    try:
        start = time.time()
        conn = get_db_connection(max_retries=1, delay=0)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        latency_ms = round((time.time() - start) * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return jsonify({
        "status": "online",
        "app_ip": get_local_ip(),
        "database": {
            "host": DB_HOST,
            "port": DB_PORT,
            "database_name": DB_NAME,
            "status": db_status,
            "latency_ms": latency_ms
        }
    })

if __name__ == '__main__':
    init_tables_if_needed()
    app.run(host='0.0.0.0', port=5000, debug=True)
