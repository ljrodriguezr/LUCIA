from flask import Flask, render_template, request, jsonify
# Importamos la instancia de MySQL desde nuestro archivo de conexión
try:
    from Conexion.conexion import mysql
except ImportError:
    import os
    import sys
    # Si la importación falla, intentamos añadir la ruta del directorio padre al PATH
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from Conexion.conexion import mysql

app = Flask(__name__)

# Configuración de la conexión a la base de datos MySQL
# Asegúrate de que estos valores coincidan con tu configuración de MariaDB
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '' # ¡No olvides cambiar esto!
app.config['MYSQL_DB'] = 'desarrollo_web'

# Inicializamos la instancia de MySQL con la configuración de la app
mysql.init_app(app)

# Tu código existente de app.py...
# Por ejemplo, tu ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para mostrar el formulario
@app.route('/formulario')
def formulario():
    return render_template('formulario.html')


# Ruta para probar la conexión a la base de datos
@app.route('/test_db')
def test_db_connection():
    try:
        # Creamos un cursor para ejecutar consultas
        cur = mysql.connection.cursor()
        # Una consulta simple para verificar la conexión
        cur.execute("SELECT 1")
        # Obtenemos el resultado
        result = cur.fetchone()
        # Cerramos el cursor
        cur.close()
        # Si la consulta fue exitosa, la conexión funciona
        return "<h1>¡Conexión a la base de datos exitosa!</h1><p>Resultado de la prueba: {}</p>".format(result)
    except Exception as e:
        # Si hay un error, lo mostramos en el navegador
        return "<h1>Error al conectar a la base de datos:</h1><p>{}</p>".format(e)

if __name__ == '__main__':
    app.run(debug=True)