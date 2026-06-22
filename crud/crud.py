from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import os, logging
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
import paho.mqtt.client as mqtt
import ssl

# Configuración MQTTS
MQTT_BROKER = os.environ.get("SERVIDOR")
MQTT_PORT = int(os.environ.get("PUERTO_MQTTS", 8883))
MQTT_USER = os.environ.get("MQTT_USR")
MQTT_PASS = os.environ.get("MQTT_PASS")

def obtener_cliente_mqtt():
    if not MQTT_BROKER:
        raise ValueError("Variable SERVIDOR nula. El contenedor no está leyendo el archivo .env.")
        
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    
    client.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)
    client.tls_insecure_set(True)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        logging.error(f"Fallo crítico en conexión MQTTS: {str(e)}")
        raise
logging.basicConfig(format='%(asctime)s - CRUD - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config["MYSQL_USER"] = os.environ["MYSQL_USER"]
app.config["MYSQL_PASSWORD"] = os.environ["MYSQL_PASSWORD"]
app.config["MYSQL_DB"] = os.environ["MYSQL_DB"]
app.config["MYSQL_HOST"] = os.environ["MYSQL_HOST"]
app.config['PERMANENT_SESSION_LIFETIME']=180
mysql = MySQL(app)

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        if not request.form.get("usuario"):
            return "el campo usuario es oblicatorio"
        elif not request.form.get("password"):
            return "el campo contraseña es oblicatorio"

        passhash=generate_password_hash(request.form.get("password"), method='scrypt', salt_length=16)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usuarios (usuario, hash) VALUES (%s,%s)", (request.form.get("usuario"), passhash[17:]))
        if mysql.connection.affected_rows():
            flash('Se agregó un usuario')
            logging.info("se agregó un usuario")
        mysql.connection.commit()
        return redirect(url_for('index'))

    return render_template('registrar.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not request.form.get("usuario"):
            return "el campo usuario es oblicatorio"
        elif not request.form.get("password"):
            return "el campo contraseña es oblicatorio"

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario LIKE %s", (request.form.get("usuario"),))
        rows=cur.fetchone()
        if(rows):
            if (check_password_hash('scrypt:32768:8:1$' + rows[2],request.form.get("password"))):
                session.permanent = True
                session["user_id"]=request.form.get("usuario")
                logging.info("se autenticó correctamente")
                return redirect(url_for('index'))
            else:
                flash('usuario o contraseña incorrecto')
                return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/')
@require_login
def index():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM dispositivos_pico')
    datos = cur.fetchall()
    cur.close()
    return render_template('index.html', dispositivos = datos)

@app.route('/add_dispositivo', methods=['POST'])
@require_login
def add_dispositivo():
    if request.method == 'POST':
        id_dispositivo = request.form['id_dispositivo']
        nombre = request.form['nombre']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO dispositivos_pico (ID_dispositivo, nombre) VALUES (%s,%s)", (id_dispositivo, nombre))
        if mysql.connection.affected_rows():
            flash('Se agregó un dispositivo')
            logging.info("se agregó un dispositivo")
            mysql.connection.commit()
    return redirect(url_for('index'))

@app.route('/borrar/<string:id>', methods = ['GET'])
@require_login
def borrar_dispositivo(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM dispositivos_pico WHERE ID_dispositivo = %s', (id,))
    if mysql.connection.affected_rows():
        flash('Se eliminó un dispositivo')
        logging.info("se eliminó un dispositivo")
        mysql.connection.commit()
    return redirect(url_for('index'))

@app.route('/editar/<string:id>', methods = ['GET'])
@require_login
def conseguir_dispositivo(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM dispositivos_pico WHERE ID_dispositivo = %s', (id,))
    datos = cur.fetchone()
    logging.info(datos)
    return render_template('editar-dispositivo.html', dispositivo = datos)

@app.route('/actualizar/<string:id>', methods=['POST'])
@require_login
def actualizar_dispositivo(id):
    if request.method == 'POST':
        nuevo_id = request.form['nuevo_id']
        nombre = request.form['nombre']
        setpoint = request.form['setpoint']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE dispositivos_pico SET ID_dispositivo=%s, nombre=%s, setpoint=%s WHERE ID_dispositivo=%s", (nuevo_id, nombre, setpoint, id))
        if mysql.connection.affected_rows():
            flash('Se actualizó un dispositivo')
            logging.info("se actualizó un dispositivo")
            mysql.connection.commit()
    return redirect(url_for('index'))

@app.route('/enviar_comando', methods=['POST'])
@require_login
def enviar_comando():
    nodo_id = request.form.get('nodo_destinatario')
    accion = request.form.get('accion')

    if not nodo_id:
        flash('Seleccione un nodo destinatario')
        return redirect(url_for('index'))

    try:
        client = obtener_cliente_mqtt()
    except Exception as e:
        flash('Error de conexión con el Broker MQTT.')
        return redirect(url_for('index'))

    try:
        if accion == 'destello':
            topico = f"{nodo_id}/destello"
            info = client.publish(topico, "1", qos=1)
            info.wait_for_publish(timeout=5.0)
            flash(f'Comando de destello enviado al nodo {nodo_id}')
            logging.info(f"Destello publicado en tópico: {topico}")

        elif accion == 'setpoint':
            nuevo_setpoint = request.form.get('nuevo_setpoint')
            if nuevo_setpoint:
                topico = f"{nodo_id}/setpoint"
                info = client.publish(topico, str(nuevo_setpoint), qos=1)
                info.wait_for_publish(timeout=5.0)
                
                cur = mysql.connection.cursor()
                cur.execute("UPDATE dispositivos_pico SET setpoint=%s WHERE ID_dispositivo=%s", (nuevo_setpoint, nodo_id))
                mysql.connection.commit()
                flash(f'Setpoint actualizado a {nuevo_setpoint} para el nodo {nodo_id}')
                logging.info(f"Setpoint publicado en tópico: {topico}")
                
    except Exception as e:
        logging.error(f"Error en la publicación MQTT: {str(e)}")
        flash('Error al transmitir el comando al Broker.')
    finally:
        client.loop_stop()
        client.disconnect()

    return redirect(url_for('index'))

@app.route("/logout")
@require_login
def logout():
    session.clear()
    logging.info("el usuario {} cerró su sesión".format(session.get("user_id")))
    return redirect(url_for('index'))