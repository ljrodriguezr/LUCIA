from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializar la aplicación Flask
app = Flask(__name__)
# ¡IMPORTANTE! Reemplaza 'una-clave-super-secreta' por una clave generada aleatoriamente en producción.
app.config['SECRET_KEY'] = 'una-clave-super-secreta' 

# --- Configuración de MySQL ---
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'desarrollo_web'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Resultados como diccionarios

# Inicializar Flask-MySQLdb y Flask-Login
mysql = MySQL(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Mensajes traducidos para Flask-Login
login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
login_manager.login_message_category = 'warning' 

# --- Modelo de Usuario ---
class User(UserMixin):
    # CORRECCIÓN 1: Argumentos opcionales para resolver el TypeError al instanciar.
    def __init__(self, id=None, username=None, password=None):  
        self.id = id
        self.username = username
        self.password = password

# Función para cargar el usuario (requerido por Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    # Usamos 'users' como la tabla de registro (según tu error más reciente)
    cur.execute("SELECT id, username, password FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        # CORRECCIÓN: Usa el orden posicional (sin id=, username=) para ser más seguro
        return User(user_data['id'], user_data['username'], user_data['password'])
    return None

# --- Rutas de Autenticación ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('registro'))
        
        if password != confirm_password:
            flash('Error: Las contraseñas no coinciden. Por favor, revísalas.', 'error')
            return redirect(url_for('registro'))

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return redirect(url_for('registro'))

        cur = mysql.connection.cursor()
        # Verificar si el usuario ya existe
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
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
            # Intenta hacer rollback si algo falla
            mysql.connection.rollback() 
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
            # CORRECCIÓN 2: Uso correcto de la indentación y llamada posicional
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            flash(f'¡Bienvenido, {username}! Has iniciado sesión con éxito.', 'success')
            return redirect(url_for('leer_productos')) 
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


# --- Rutas del CRUD de Productos ---

@app.route('/')
@login_required
def index():
    return redirect(url_for('leer_productos'))

# 1. Leer Productos (Read)
@app.route('/productos')
@login_required
def leer_productos():
    cur = mysql.connection.cursor() 
    # ASUNCIÓN: El campo primario de la tabla 'productos' se llama 'id'
    cur.execute("SELECT * FROM productos ORDER BY id DESC")
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
            mysql.connection.rollback()
            cur.close()
            flash('Ocurrió un error al guardar el producto. Inténtalo de nuevo.', 'error')
            return redirect(url_for('crear_producto'))
    
    # Renderiza el formulario si es GET
    return render_template('formulario_producto.html', producto=None, action='crear')

# 3. Actualizar Producto (Update)
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
# ASUNCIÓN: Cambiamos 'id_producto' por 'id' para estandarizar
def editar_producto(id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        stock = request.form['stock']
        
        # Validación de Datos (similar a crear)
        if not nombre or not precio or not stock:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('editar_producto', id=id))
        
        try:
            precio_float = float(precio)
            stock_int = int(stock)
            if precio_float <= 0 or stock_int < 0:
                flash('El precio debe ser positivo y el stock no puede ser negativo.', 'error')
                return redirect(url_for('editar_producto', id=id))
        except ValueError:
            flash('El precio debe ser un número decimal y el stock un entero.', 'error')
            return redirect(url_for('editar_producto', id=id))
        # Fin de la Validación
        
        try:
            # ASUNCIÓN: Cambiamos 'id_producto' por 'id' en la consulta
            query = "UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s"
            cur.execute(query, (nombre, precio_float, stock_int, id))
            mysql.connection.commit()
            cur.close()
            flash(f'Producto "{nombre}" actualizado exitosamente.', 'success')
            return redirect(url_for('leer_productos'))
        except Exception as e:
            print(f"Error al actualizar producto: {e}")
            mysql.connection.rollback()
            cur.close()
            flash('Ocurrió un error al actualizar el producto. Inténtalo de nuevo.', 'error')
            return redirect(url_for('editar_producto', id=id))
    
    # Si es GET, se carga el producto para mostrarlo en el formulario
    # ASUNCIÓN: Cambiamos 'id_producto' por 'id' en la consulta
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()
    cur.close()

    if producto is None:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('leer_productos'))
        
    # Se pasa el objeto 'producto' y la acción 'editar'
    return render_template('formulario_producto.html', producto=producto, action='editar', id=id)

# 4. Eliminar Producto (Delete)
@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
# ASUNCIÓN: Cambiamos 'id_producto' por 'id'
def eliminar_producto(id):
    try:
        cur = mysql.connection.cursor()
        # ASUNCIÓN: Cambiamos 'id_producto' por 'id' en la consulta
        query = "DELETE FROM productos WHERE id = %s"
        cur.execute(query, (id,))
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
        mysql.connection.rollback()
        flash('Ocurrió un error al intentar eliminar el producto.', 'error')
        return redirect(url_for('leer_productos'))


# -----------------------------------------------
# --- CRUD de Clientes ---
# -----------------------------------------------

# 1. Leer Clientes (Read)
@app.route('/clientes')
@login_required
def leer_clientes():
    cur = mysql.connection.cursor() 
    # ASUNCIÓN: El campo primario de la tabla 'clientes' se llama 'id'
    cur.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = cur.fetchall()
    cur.close()
    
    return render_template('clientes.html', clientes=clientes)

# 2. Crear Cliente (Create)
@app.route('/crear_cliente', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    if request.method == 'POST':
        # Asumo que estos son los campos según tu código y el diseño de la DB
        nombre = request.form['nombre']
        apellido = request.form['apellido'] # Agregando campo 'apellido' de la DB
        documento = request.form['documento'] # Agregando campo 'documento'
        direccion = request.form['direccion'] # Agregando campo 'direccion'
        email = request.form['email']
        telefono = request.form['telefono'] 

        # --- Validación de Datos ---
        if not nombre or not apellido or not documento or not direccion or not email or not telefono:
            flash('Todos los campos del cliente son obligatorios.', 'error')
            return redirect(url_for('crear_cliente'))
        # ---------------------------

        try:
            cur = mysql.connection.cursor()
            # Insertamos el 'usuario_id' del usuario actual (current_user)
            query = """
            INSERT INTO clientes (usuario_id, nombre, apellido, documento, direccion, email, telefono) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                current_user.id, # Clave Foránea del usuario logueado
                nombre, 
                apellido, 
                documento, 
                direccion, 
                email, 
                telefono
            ))
            mysql.connection.commit()
            cur.close()
            flash(f'Cliente "{nombre} {apellido}" creado exitosamente.', 'success')
            return redirect(url_for('leer_clientes'))
        except Exception as e:
            print(f"Error al insertar cliente: {e}")
            mysql.connection.rollback()
            cur.close()
            # Este error puede ser por duplicidad de email/documento o clave foránea rota
            flash('Ocurrió un error al guardar el cliente. Revisa si el email o documento ya existen. Detalle: ' + str(e), 'error')
            return redirect(url_for('crear_cliente'))
    
    # Renderiza el formulario si es GET
    return render_template('formulario_cliente.html', cliente=None, action='crear')

# 3. Actualizar Cliente (Update)
@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@login_required
# ASUNCIÓN: Cambiamos 'id_cliente' por 'id'
def editar_cliente(id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        documento = request.form['documento']
        direccion = request.form['direccion']
        email = request.form['email']
        telefono = request.form['telefono']
        
        # Validación de Datos
        if not nombre or not apellido or not documento or not direccion or not email or not telefono:
            flash('Todos los campos del cliente son obligatorios.', 'error')
            return redirect(url_for('editar_cliente', id=id))
        
        try:
            query = """
            UPDATE clientes 
            SET nombre=%s, apellido=%s, documento=%s, direccion=%s, email=%s, telefono=%s 
            WHERE id=%s
            """
            cur.execute(query, (nombre, apellido, documento, direccion, email, telefono, id))
            mysql.connection.commit()
            cur.close()
            flash(f'Cliente "{nombre} {apellido}" actualizado exitosamente.', 'success')
            return redirect(url_for('leer_clientes'))
        except Exception as e:
            print(f"Error al actualizar cliente: {e}")
            mysql.connection.rollback()
            cur.close()
            flash('Ocurrió un error al actualizar el cliente. Inténtalo de nuevo.', 'error')
            return redirect(url_for('editar_cliente', id=id))
    
    # Si es GET, se carga el cliente para mostrarlo en el formulario
    cur.execute("SELECT * FROM clientes WHERE id = %s", (id,))
    cliente = cur.fetchone()
    cur.close()

    if cliente is None:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('leer_clientes'))
        
    # Se pasa el objeto 'cliente' y la acción 'editar'
    return render_template('formulario_cliente.html', cliente=cliente, action='editar', id=id)

# 4. Eliminar Cliente (Delete)
@app.route('/eliminar_cliente/<int:id>', methods=['POST'])
@login_required
# ASUNCIÓN: Cambiamos 'id_cliente' por 'id'
def eliminar_cliente(id):
    try:
        cur = mysql.connection.cursor()
        query = "DELETE FROM clientes WHERE id = %s"
        cur.execute(query, (id,))
        mysql.connection.commit()
        
        if cur.rowcount > 0:
            flash('Cliente eliminado exitosamente.', 'success')
        else:
            flash('Cliente no encontrado para eliminar.', 'error')

        cur.close()
        return redirect(url_for('leer_clientes'))
    except Exception as e:
        print(f"Error al eliminar cliente: {e}")
        mysql.connection.rollback()
        flash('Ocurrió un error al intentar eliminar el cliente. Asegúrate de que no tenga formularios asociados.', 'error')
        return redirect(url_for('leer_clientes'))


# -----------------------------------------------
# --- EJECUCIÓN ---
# -----------------------------------------------
if __name__ == '__main__':
    # CORRECCIÓN 3: Corregir el nombre de la variable '__main__' (doble guion bajo)
    app.run(debug=True)