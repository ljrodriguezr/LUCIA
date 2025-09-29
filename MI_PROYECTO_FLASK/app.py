from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializar la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'una-clave-super-secreta' # ¡Mantén esta clave segura!

# --- Configuración de MySQL (Asegúrate de que estas credenciales sean correctas) ---
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'desarrollo_web'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Para que los resultados sean diccionarios, más fácil de usar en Jinja2

# Inicializar Flask-MySQLdb y Flask-Login
mysql = MySQL(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ESTE ES EL PRIMER CAMBIO: Traducir el mensaje por defecto de login_required
login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
login_manager.login_message_category = 'warning' 

# --- Modelo de Usuario ---
class User(UserMixin):
    def _init_(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Función para cargar el usuario
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        # Usa el nombre de la columna para acceder a los datos
        return User(id=user_data['id'], username=user_data['username'], password=user_data['password'])
    return None

# --- Rutas de Autenticación (Alertas traducidas) ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validación inicial de campos vacíos, incluyendo la confirmación
        if not username or not password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('registro'))
        
        # VALIDAR QUE LAS CONTRASEÑAS COINCIDAN
        if password != confirm_password:
            flash('Error: Las contraseñas no coinciden. Por favor, revísalas.', 'error')
            return redirect(url_for('registro'))

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return redirect(url_for('registro'))

        cur = mysql.connection.cursor()
        # Verificar si el usuario ya existe
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cur.fetchone()
        
        if existing_user:
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'error')
            cur.close()
            return redirect(url_for('registro'))
        
        # HASHEAR Y GUARDAR
        hashed_password = generate_password_hash(password, method='scrypt')
        
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            mysql.connection.commit()
            cur.close()
            flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error al registrar el usuario: {e}")
            cur.close()
            flash('Ocurrió un error inesperado al registrar el usuario. Inténtalo de nuevo.', 'error')
            return redirect(url_for('registro'))
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirige a la lista de productos si ya está autenticado
    if current_user.is_authenticated:
        return redirect(url_for('leer_productos'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,)) 
        user_data = cur.fetchone()
        cur.close()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'], password=user_data['password'])
            login_user(user)
            flash(f'¡Bienvenido, {username}! Has iniciado sesión con éxito.', 'success')
            return redirect(url_for('leer_productos')) # Redirige a la lista de productos
        else:
            flash('Inicio de sesión fallido. Revisa tu nombre de usuario y contraseña.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))


# --- Rutas del CRUD de Productos (Alertas traducidas) ---

# Ruta principal: Redirige a la lista de productos
@app.route('/')
@login_required
def index():
    return redirect(url_for('leer_productos'))

# 1. Leer Productos (Read)
@app.route('/productos')
@login_required
def leer_productos():
    cur = mysql.connection.cursor() 
    cur.execute("SELECT * FROM productos ORDER BY id_producto DESC")
    productos = cur.fetchall()
    cur.close()
    
    return render_template('productos.html', productos=productos)

# 2. Crear Producto (Create)
@app.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']

        # --- Validación de Datos ---
        if not nombre or not precio or not stock:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('crear_producto'))

        try:
            precio_float = float(precio)
            stock_int = int(stock)
            if precio_float <= 0 or stock_int < 0:
                flash('El precio debe ser positivo y el stock no puede ser negativo.', 'error')
                return redirect(url_for('crear_producto'))
        except ValueError:
            flash('El precio debe ser un número decimal y el stock un entero.', 'error')
            return redirect(url_for('crear_producto'))
        # ---------------------------

        try:
            cur = mysql.connection.cursor()
            query = "INSERT INTO productos (nombre, precio, stock) VALUES (%s, %s, %s)"
            cur.execute(query, (nombre, precio_float, stock_int))
            mysql.connection.commit()
            cur.close()
            flash(f'Producto "{nombre}" creado exitosamente.', 'success')
            return redirect(url_for('leer_productos'))
        except Exception as e:
            print(f"Error al insertar producto: {e}")
            flash('Ocurrió un error al guardar el producto. Inténtalo de nuevo.', 'error')
            return redirect(url_for('crear_producto'))
    
    # Renderiza el formulario si es GET
    return render_template('formulario_producto.html', producto=None, action='crear')

# 3. Actualizar Producto (Update)
@app.route('/editar/<int:id_producto>', methods=['GET', 'POST'])
@login_required
def editar_producto(id_producto):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        
        # Validación de Datos (similar a crear)
        if not nombre or not precio or not stock:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('editar_producto', id_producto=id_producto))
        
        try:
            precio_float = float(precio)
            stock_int = int(stock)
            if precio_float <= 0 or stock_int < 0:
                flash('El precio debe ser positivo y el stock no puede ser negativo.', 'error')
                return redirect(url_for('editar_producto', id_producto=id_producto))
        except ValueError:
            flash('El precio debe ser un número decimal y el stock un entero.', 'error')
            return redirect(url_for('editar_producto', id_producto=id_producto))
        # Fin de la Validación
        
        try:
            query = "UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id_producto=%s"
            cur.execute(query, (nombre, precio_float, stock_int, id_producto))
            mysql.connection.commit()
            cur.close()
            flash(f'Producto "{nombre}" actualizado exitosamente.', 'success')
            return redirect(url_for('leer_productos'))
        except Exception as e:
            print(f"Error al actualizar producto: {e}")
            flash('Ocurrió un error al actualizar el producto. Inténtalo de nuevo.', 'error')
            return redirect(url_for('editar_producto', id_producto=id_producto))
    
    # Si es GET, se carga el producto para mostrarlo en el formulario
    cur.execute("SELECT * FROM productos WHERE id_producto = %s", (id_producto,))
    producto = cur.fetchone()
    cur.close()

    if producto is None:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('leer_productos'))
        
    # Se pasa el objeto 'producto' y la acción 'editar'
    return render_template('formulario_producto.html', producto=producto, action='editar', id_producto=id_producto)

# 4. Eliminar Producto (Delete)
@app.route('/eliminar/<int:id_producto>', methods=['POST'])
@login_required
def eliminar_producto(id_producto):
    try:
        cur = mysql.connection.cursor()
        query = "DELETE FROM productos WHERE id_producto = %s"
        cur.execute(query, (id_producto,))
        mysql.connection.commit()
        
        # Revisa si se eliminó alguna fila
        if cur.rowcount > 0:
            flash('Producto eliminado exitosamente.', 'success')
        else:
            flash('Producto no encontrado para eliminar.', 'error')

        cur.close()
        return redirect(url_for('leer_productos'))
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        flash('Ocurrió un error al intentar eliminar el producto.', 'error')
        return redirect(url_for('leer_productos'))


# -----------------------------------------------
# --- NUEVAS RUTAS: CRUD de Clientes (Cliente) ---
# -----------------------------------------------

# 1. Leer Clientes (Read)
@app.route('/clientes')
@login_required
def leer_clientes():
    cur = mysql.connection.cursor() 
    # Asegúrate de que tu tabla se llama 'clientes' o 'cliente' en la DB
    cur.execute("SELECT * FROM clientes ORDER BY id_cliente DESC")
    clientes = cur.fetchall()
    cur.close()
    
    return render_template('clientes.html', clientes=clientes)

# 2. Crear Cliente (Create)
@app.route('/crear_cliente', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono'] # Nuevo campo

        # --- Validación de Datos ---
        if not nombre or not email or not telefono:
            flash('Todos los campos del cliente son obligatorios.', 'error')
            return redirect(url_for('crear_cliente'))
        # ---------------------------

        try:
            cur = mysql.connection.cursor()
            # Asumiendo que la tabla tiene id_cliente, nombre, email, telefono
            query = "INSERT INTO clientes (nombre, email, telefono) VALUES (%s, %s, %s)"
            cur.execute(query, (nombre, email, telefono))
            mysql.connection.commit()
            cur.close()
            flash(f'Cliente "{nombre}" creado exitosamente.', 'success')
            return redirect(url_for('leer_clientes'))
        except Exception as e:
            print(f"Error al insertar cliente: {e}")
            flash('Ocurrió un error al guardar el cliente. Inténtalo de nuevo.', 'error')
            return redirect(url_for('crear_cliente'))
    
    # Renderiza el formulario si es GET
    return render_template('formulario_cliente.html', cliente=None, action='crear')

# 3. Actualizar Cliente (Update)
@app.route('/editar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id_cliente):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        
        # Validación de Datos
        if not nombre or not email or not telefono:
            flash('Todos los campos del cliente son obligatorios.', 'error')
            return redirect(url_for('editar_cliente', id_cliente=id_cliente))
        # Fin de la Validación
        
        try:
            query = "UPDATE clientes SET nombre=%s, email=%s, telefono=%s WHERE id_cliente=%s"
            cur.execute(query, (nombre, email, telefono, id_cliente))
            mysql.connection.commit()
            cur.close()
            flash(f'Cliente "{nombre}" actualizado exitosamente.', 'success')
            return redirect(url_for('leer_clientes'))
        except Exception as e:
            print(f"Error al actualizar cliente: {e}")
            flash('Ocurrió un error al actualizar el cliente. Inténtalo de nuevo.', 'error')
            return redirect(url_for('editar_cliente', id_cliente=id_cliente))
    
    # Si es GET, se carga el cliente para mostrarlo en el formulario
    cur.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
    cliente = cur.fetchone()
    cur.close()

    if cliente is None:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('leer_clientes'))
        
    # Se pasa el objeto 'cliente' y la acción 'editar'
    return render_template('formulario_cliente.html', cliente=cliente, action='editar', id_cliente=id_cliente)

# 4. Eliminar Cliente (Delete)
@app.route('/eliminar_cliente/<int:id_cliente>', methods=['POST'])
@login_required
def eliminar_cliente(id_cliente):
    try:
        cur = mysql.connection.cursor()
        query = "DELETE FROM clientes WHERE id_cliente = %s"
        cur.execute(query, (id_cliente,))
        mysql.connection.commit()
        
        # Revisa si se eliminó alguna fila
        if cur.rowcount > 0:
            flash('Cliente eliminado exitosamente.', 'success')
        else:
            flash('Cliente no encontrado para eliminar.', 'error')

        cur.close()
        return redirect(url_for('leer_clientes'))
    except Exception as e:
        print(f"Error al eliminar cliente: {e}")
        flash('Ocurrió un error al intentar eliminar el cliente.', 'error')
        return redirect(url_for('leer_clientes'))

# --- Rutas antiguas que ya no se usan (comentadas) ---
# @app.route('/profile')
# @login_required
# def profile():
#    return redirect(url_for('leer_productos')) 

# @app.route('/')
# def home():
#    return render_template('index.html')

# @app.route('/formulario')
# def formulario():
#    return render_template('formulario.html')


if __name__ == '_main_':
    app.run(debug=True)