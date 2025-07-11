
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import jwt
import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, IntegerField, TextAreaField, SubmitField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))

app.config['SECRET_KEY'] = 'change_this_secret'

USERS = {
    'admin@ia.com': {
        'password': 'adminpass',
        'rol': 'Administrador'
    },
    'bodega@ia.com': {
        'password': 'bodegapass',
        'rol': 'Personal Bodega'
    },
    'tecnico@ia.com': {
        'password': 'tecnicopass',
        'rol': 'Tecnico Desmantelamiento'
    },
    'cliente@ia.com': {
        'password': 'clientepass',
        'rol': 'Proveedor'
    }
}

ALLOWED_ROLES = list(set(u['rol'] for u in USERS.values()))



telefonos = {}
componentes = {}
proveedores = {}
pedidos = {}

bodega = {}
articulos = []


def load_data():
    if os.path.exists(DATA_FILE):
        import json
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            telefonos.update(data.get('telefonos', {}))
            componentes.update(data.get('componentes', {}))
            proveedores.update(data.get('proveedores', {}))
            pedidos.update(data.get('pedidos', {}))
            bodega.update(data.get('bodega', {}))
            articulos.extend(data.get('articulos', []))

def save_data():
    import json
    data = {
        'telefonos': telefonos,
        'componentes': componentes,
        'proveedores': proveedores,
        'pedidos': pedidos,
        'bodega': bodega,
        'articulos': articulos,
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


load_data()


# Helpers

def generate_token(email, rol):
    payload = {
        'email': email,
        'rol': rol,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def require_auth(role=None):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not auth:
                return jsonify({'error': 'Auth required'}), 401
            try:
                data = jwt.decode(auth, app.config['SECRET_KEY'], algorithms=['HS256'])
                if role and data['rol'] not in role:
                    return jsonify({'error': 'Forbidden'}), 403
                request.user = data
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.DecodeError:
                return jsonify({'error': 'Invalid token'}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator



# ----- Flask-WTF Forms for web views -----
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Ingresar')


class PhoneForm(FlaskForm):
    estado_inicial = StringField('Estado Inicial', validators=[DataRequired()])
    origen = StringField('Origen', validators=[DataRequired()])
    detalles_usuario = TextAreaField('Detalles del Usuario')
    image_url = StringField('URL Imagen')
    submit = SubmitField('Guardar')


class ComponentForm(FlaskForm):
    tipo = StringField('Tipo', validators=[DataRequired()])
    marca = StringField('Marca', validators=[DataRequired()])
    modelo = StringField('Modelo', validators=[DataRequired()])
    estado = StringField('Estado', validators=[DataRequired()])
    precio = FloatField('Precio', validators=[DataRequired()])
    image_url = StringField('URL Imagen')
    submit = SubmitField('Guardar')


class ProviderForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    contacto = StringField('Contacto', validators=[DataRequired()])
    submit = SubmitField('Guardar')


class OrderForm(FlaskForm):
    proveedor = SelectField('Proveedor', validators=[DataRequired()])
    componentes_ids = StringField('IDs de Componentes (separados por coma)', validators=[DataRequired()])
    metodo_pago = SelectField('Método de Pago', choices=[('Tarjeta','Tarjeta'),('Mercado Pago','Mercado Pago')], validators=[DataRequired()])
    submit = SubmitField('Crear Pedido')


class WarehouseForm(FlaskForm):
    item = StringField('Ítem', validators=[DataRequired()])
    qty = IntegerField('Cantidad', validators=[DataRequired()])
    submit = SubmitField('Guardar')


class ArticleForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired()])
    contenido = TextAreaField('Contenido', validators=[DataRequired()])
    submit = SubmitField('Publicar')


def login_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user' not in session:
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('web_login'))
        return view_func(*args, **kwargs)
    return wrapped


# --- Auth Endpoints ---
@app.post('/login')
def login():
    data = request.json
    email = data.get('email')
    pwd = data.get('password')
    user = USERS.get(email)
    if user and user['password'] == pwd:
        token = generate_token(email, user['rol'])
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# --- User Management ---
@app.post('/users')
@require_auth(role=['Administrador'])
def create_user():
    data = request.json
    email = data.get('email')
    pwd = data.get('password')
    rol = data.get('rol')
    if email in USERS:
        return jsonify({'error': 'exists'}), 400
    if rol not in ALLOWED_ROLES:
        return jsonify({'error': 'invalid role'}), 400
    USERS[email] = {'password': pwd, 'rol': rol}
    return jsonify({'status': 'ok'}), 201

@app.get('/users')
@require_auth(role=['Administrador'])
def list_users():
    return jsonify([{ 'email': e, 'rol': u['rol'] } for e, u in USERS.items()])

# --- Phone Collection ---
@app.post('/phones')
@require_auth(role=['Administrador','Personal Bodega'])
def register_phone():
    data = request.json
    id_tel = f"TEL-{len(telefonos)+1:04d}"
    telefono = {
        'id': id_tel,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'estado_inicial': data.get('estado_inicial'),
        'origen': data.get('origen'),
        'procesamiento': 'Pendiente Desmantelamiento',
        'detalles_usuario': data.get('detalles_usuario'),
        'image_url': data.get('image_url')
    }
    telefonos[id_tel] = telefono
    return jsonify(telefono), 201

@app.get('/phones')
@require_auth(role=ALLOWED_ROLES)
def list_phones():
    return jsonify(list(telefonos.values()))

# --- Inventory Components ---
@app.post('/components')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def add_component():
    data = request.json
    idc = f"COMP-{len(componentes)+10001:05d}"
    comp = {
        'id': idc,
        'tipo': data.get('tipo'),
        'marca': data.get('marca'),
        'modelo': data.get('modelo'),
        'estado': data.get('estado'),
        'precio': data.get('precio'),
        'disponible': True,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'image_url': data.get('image_url')
    }
    componentes[idc] = comp
    return jsonify(comp), 201

@app.get('/components')
@require_auth(role=ALLOWED_ROLES)
def list_components():
    return jsonify(list(componentes.values()))

# --- Providers ---
@app.post('/providers')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def add_provider():
    data = request.json
    pid = f"PROV-{len(proveedores)+1:04d}"
    prov = {'id': pid, 'nombre': data.get('nombre'), 'contacto': data.get('contacto')}
    proveedores[pid] = prov
    return jsonify(prov), 201

@app.get('/providers')
@require_auth(role=ALLOWED_ROLES)
def list_providers():
    return jsonify(list(proveedores.values()))

# --- Orders ---
@app.post('/orders')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def create_order():
    data = request.json
    pid = data.get('proveedor')
    if pid not in proveedores:
        return jsonify({'error': 'invalid provider'}), 400
    order_id = f"PEDIDO-{len(pedidos)+1:04d}"
    items = []
    total = 0
    for item in data.get('items', []):
        cid = item['id']
        comp = componentes.get(cid)
        if not comp or not comp['disponible']:
            return jsonify({'error': f'component {cid} unavailable'}), 400
        comp['disponible'] = False
        items.append({'id': cid, 'precio': comp['precio']})
        total += comp['precio']
    pedido = {
        'id': order_id,
        'proveedor': pid,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'items': items,
        'metodo_pago': data.get('metodo_pago'),
        'estado': 'Pendiente',
        'total': total
    }
    pedidos[order_id] = pedido
    return jsonify(pedido), 201

@app.get('/orders')
@require_auth(role=ALLOWED_ROLES)
def list_orders():
    return jsonify(list(pedidos.values()))

# --- Bodega ---
@app.post('/warehouse')
@require_auth(role=['Administrador','Personal Bodega'])
def add_item():
    data = request.json
    name = data.get('item')
    qty = int(data.get('qty', 0))
    if qty <= 0:
        return jsonify({'error': 'qty'}), 400
    bodega[name] = bodega.get(name, 0) + qty
    return jsonify({'item': name, 'qty': bodega[name]})

@app.get('/warehouse')
@require_auth(role=ALLOWED_ROLES)
def view_warehouse():
    return jsonify(bodega)

# --- Educational articles ---
@app.post('/articles')
@require_auth(role=['Administrador'])
def add_article():
    data = request.json
    art = {
        'titulo': data.get('titulo'),
        'contenido': data.get('contenido'),
        'fecha': datetime.datetime.utcnow().date().isoformat()
    }
    articulos.append(art)
    return jsonify(art), 201

@app.get('/articles')
@require_auth(role=ALLOWED_ROLES)
def list_articles():
    return jsonify(articulos)



# ------- Web Views -------

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', user=session['user'])
    return redirect(url_for('web_login'))


@app.route('/login', methods=['GET', 'POST'])
def web_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        pwd = form.password.data
        user = USERS.get(email)
        if user and user['password'] == pwd:
            session['user'] = {'email': email, 'rol': user['rol']}
            flash('Bienvenido', 'info')
            return redirect(url_for('index'))
        flash('Credenciales incorrectas', 'error')
    return render_template('login.html', form=form)


@app.route('/logout')
def web_logout():
    session.pop('user', None)
    flash('Sesión finalizada', 'info')
    return redirect(url_for('web_login'))


@app.route('/phones')
@login_required
def phones_view():
    return render_template('phones.html', phones=list(telefonos.values()))


@app.route('/phones/new', methods=['GET', 'POST'])
@login_required
def phone_new():
    form = PhoneForm()
    if form.validate_on_submit():
        id_tel = f"TEL-{len(telefonos)+1:04d}"
        telefono = {
            'id': id_tel,
            'fecha': datetime.datetime.utcnow().isoformat(),
            'estado_inicial': form.estado_inicial.data,
            'origen': form.origen.data,
            'procesamiento': 'Pendiente Desmantelamiento',
            'detalles_usuario': form.detalles_usuario.data,
            'image_url': form.image_url.data
        }
        telefonos[id_tel] = telefono
        save_data()
        flash('Teléfono registrado', 'info')
        return redirect(url_for('phones_view'))
    return render_template('phone_form.html', form=form)


@app.route('/components')
@login_required
def components_view():
    return render_template('components.html', components=list(componentes.values()))


@app.route('/components/new', methods=['GET', 'POST'])
@login_required
def component_new():
    form = ComponentForm()
    if form.validate_on_submit():
        idc = f"COMP-{len(componentes)+10001:05d}"
        comp = {
            'id': idc,
            'tipo': form.tipo.data,
            'marca': form.marca.data,
            'modelo': form.modelo.data,
            'estado': form.estado.data,
            'precio': form.precio.data,
            'disponible': True,
            'fecha': datetime.datetime.utcnow().isoformat(),
            'image_url': form.image_url.data
        }
        componentes[idc] = comp
        save_data()
        flash('Componente añadido', 'info')
        return redirect(url_for('components_view'))
    return render_template('component_form.html', form=form)


@app.route('/providers')
@login_required
def providers_view():
    return render_template('providers.html', providers=list(proveedores.values()))


@app.route('/providers/new', methods=['GET', 'POST'])
@login_required
def provider_new():
    form = ProviderForm()
    if form.validate_on_submit():
        pid = f"PROV-{len(proveedores)+1:04d}"
        proveedor = {'id': pid, 'nombre': form.nombre.data, 'contacto': form.contacto.data}
        proveedores[pid] = proveedor
        save_data()
        flash('Proveedor registrado', 'info')
        return redirect(url_for('providers_view'))
    return render_template('provider_form.html', form=form)


@app.route('/orders')
@login_required
def orders_view():
    return render_template('orders.html', orders=list(pedidos.values()))


@app.route('/orders/new', methods=['GET', 'POST'])
@login_required
def order_new():
    form = OrderForm()
    form.proveedor.choices = [(pid, prov['nombre']) for pid, prov in proveedores.items()]
    if form.validate_on_submit():
        pid = form.proveedor.data
        comps_ids = [c.strip() for c in form.componentes_ids.data.split(',') if c.strip()]
        order_id = f"PEDIDO-{len(pedidos)+1:04d}"
        items = []
        total = 0
        for cid in comps_ids:
            comp = componentes.get(cid)
            if comp and comp['disponible']:
                comp['disponible'] = False
                items.append({'id': cid, 'precio': comp['precio']})
                total += comp['precio']
            else:
                flash(f'Componente {cid} no disponible', 'error')
                return redirect(url_for('order_new'))
        pedido = {
            'id': order_id,
            'proveedor': pid,
            'fecha': datetime.datetime.utcnow().isoformat(),
            'items': items,
            'metodo_pago': form.metodo_pago.data,
            'estado': 'Pendiente',
            'total': total
        }
        pedidos[order_id] = pedido
        save_data()
        flash('Pedido creado', 'info')
        return redirect(url_for('orders_view'))
    return render_template('order_form.html', form=form)


@app.route('/warehouse')
@login_required
def warehouse_view():
    return render_template('warehouse.html', items=bodega)


@app.route('/warehouse/new', methods=['GET', 'POST'])
@login_required
def warehouse_new():
    form = WarehouseForm()
    if form.validate_on_submit():
        item = form.item.data
        qty = form.qty.data
        bodega[item] = bodega.get(item, 0) + qty
        save_data()
        flash('Inventario actualizado', 'info')
        return redirect(url_for('warehouse_view'))
    return render_template('warehouse_form.html', form=form)


@app.route('/articles')
@login_required
def articles_view():
    return render_template('articles.html', articles=articulos)


@app.route('/articles/new', methods=['GET', 'POST'])
@login_required
def article_new():
    if session['user']['rol'] != 'Administrador':
        flash('Solo el administrador puede publicar artículos', 'error')
        return redirect(url_for('articles_view'))
    form = ArticleForm()
    if form.validate_on_submit():
        art = {
            'titulo': form.titulo.data,
            'contenido': form.contenido.data,
            'fecha': datetime.datetime.utcnow().date().isoformat()
        }
        articulos.append(art)
        save_data()
        flash('Artículo agregado', 'info')
        return redirect(url_for('articles_view'))
    return render_template('article_form.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
