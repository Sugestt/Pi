import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask,redirect,url_for,render_template,request,jsonify,send_file, session
from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
import hashlib
from bson import ObjectId
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app=Flask(__name__)

app.config['SECRET_KEY'] = 'SPARTA'
TOKEN_KEY = 'mytoken'

UPLOAD_FOLDER = 'uploads/buktitf'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/',methods=['GET','POST'])
def home():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']
        except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
            return redirect(url_for('masukP'))
    return render_template('index.html', username=username)

@app.route('/masukA',methods=['GET','POST'])
def masukA():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = db.admin.find_one({'username': username})
        if admin and check_password_hash(admin['password'], password):
            token = jwt.encode({'id': username}, app.config['SECRET_KEY'], algorithm='HS256')
            response = redirect(url_for('dashboard'))
            response.set_cookie(TOKEN_KEY, token)
            return response
        return jsonify({'message': 'Username dan kata sandi salah'}), 401
    
    message = request.args.get('msg', '')
    return render_template('masukA.html', message=message)

@app.route("/sign_in_adm", methods=["POST"])
def sign_in_adm():
   username_receive = request.form["username_give"]
   password_receive = request.form["password_give"]
   pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
   result = db.admin.find_one(
       {
           "username": username_receive,
           "password": pw_hash,
       }
   )
   if result:
       payload = {
           "id": username_receive,
           "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
       }
       token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")

       return jsonify(
           {
               "result": "success",
               "token": token,
           }
       )
   else:
       return jsonify(
           {
               "result": "fail",
               "msg": "Kami tidak dapat menemukan pengguna dengan kombinasi username/kata sandi tersebut",
           }
       )

@app.route('/sign_outadm', methods=['POST'])
def sign_outadm():
    response = jsonify({'result': 'success'})
    response.set_cookie(TOKEN_KEY, '', max_age=0)
    return response

@app.route('/masukP',methods=['GET','POST'])
def masukP():
    return render_template('masukP.html')

@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")

        session['username'] = username_receive

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "Kami tidak dapat menemukan pengguna dengan kombinasi username/kata sandi tersebut",
            }
        )

@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               
        "password": password_hash,                                  
        "profile_name": username_receive,
        "profile_info": ""                                          
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form.get('username_give')
    exists = bool(db.users.find_one({'username': username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/sign_out', methods=['POST'])
def sign_out():
    session.pop('username', None)
    return jsonify({'result': 'success', 'msg': 'Berhasil keluar'})

@app.route('/pesanan',methods=['GET','POST'])
def pesanan():
    return render_template('pesanan.html')

@app.route('/kategori', methods=['GET', 'POST'])
def kategori():
    kategoris = list(db.kategori.find({}))
    return render_template('kategori.html', kategoris=kategoris)

@app.route('/kategori/<kategori_name>', methods=['GET'])
def kategori_detail(kategori_name):
    token_receive = request.cookies.get("mytoken")
    user_info = None
    if token_receive:
        try:
            payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])
            user_info = db.users.find_one({"username": payload["id"]})
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukP'))
        except jwt.InvalidTokenError:
            return redirect(url_for('masukP'))

    serums = list(db.serum.find({"kategori": kategori_name.capitalize()}))
    kategori = db.kategori.find_one({'route': kategori_name})
    
    if kategori_name == 'acne':
        return render_template('acne.html', serums=serums, kategori="Acne", user_info=user_info)
    elif kategori_name == 'aging':
        return render_template('aging.html', serums=serums, kategori="Aging", user_info=user_info)
    elif kategori_name == 'hydrating':
        return render_template('hydrating.html', serums=serums, kategori="Hydrating", user_info=user_info)
    elif kategori_name == 'exfoliating':
        return render_template('exfoliating.html', serums=serums, kategori="Exfoliating", user_info=user_info)
    elif kategori_name == 'brightening':
        return render_template('brightening.html', serums=serums, kategori="Brightening", user_info=user_info)
    elif kategori_name == 'repairing':
        return render_template('repairing.html', serums=serums, kategori="Repairing", user_info=user_info)
    else:
        return "Kategori tidak ditemukan", 404

@app.route('/detail/<_id>', methods=['GET'])
def detail(_id):
    try:
        serum = db.serum.find_one({"_id": ObjectId(_id)})
        if serum:
            return render_template('detail.html', serum=serum, quantity=0)
        else:
            return "Produk tidak ditemukan", 404
    except Exception as e:
        return str(e), 400

@app.route('/transaksi_form', methods=['POST'])
def transaksi_form():
    serum_id = request.form['serum_id']
    quantity = int(request.form['quantity'])
    try:
        serum = db.serum.find_one({"_id": ObjectId(serum_id)})
        if serum:
            total_pembayaran = serum['harga'] * quantity
            return render_template('transaksi.html', serum=serum, quantity=quantity, total_pembayaran=total_pembayaran)
        else:
            return "Produk tidak ditemukan", 404
    except Exception as e:
        return str(e), 400

@app.route('/transaksi', methods=['POST'])
def transaksi():
    token = request.cookies.get(TOKEN_KEY)
    if not token:
        return redirect(url_for('masukP'))

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        username = payload['id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return redirect(url_for('masukP'))

    nama = request.form['nama']
    telepon = request.form['telepon']
    alamat = request.form['alamat']
    serum_id = request.form['serum_id']
    quantity = int(request.form['quantity'])
    bukti_transfer = request.files['bukti_transfer']

    serum = db.serum.find_one({"_id": ObjectId(serum_id)})
    if not serum:
        return "Serum tidak ditemukan", 404
    
    total_pembayaran = serum['harga'] * quantity

    if bukti_transfer:
        filename = secure_filename(bukti_transfer.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        bukti_transfer.save(file_path)

        transaksi = {
            "username": username,
            "nama": nama,
            "telepon": telepon,
            "alamat": alamat,
            "serum_id": serum_id,
            "quantity": quantity,
            "bukti_transfer": filename
        }
        db.transaksi.insert_one(transaksi)

        pesanan = {
            "serum_id": serum_id,
            "username": username,
            "nama": nama,
            'jasa_kirim': "",
            'nomor_resi': "",
            'keterangan': ""
        }
        db.pesanan.insert_one(pesanan)
    return render_template('index.html', serum=serum, quantity=quantity, total_pembayaran=total_pembayaran)

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

@app.route('/pesanan_saya', methods=['GET'])
def pesanan_saya():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    pesanan_list = list(db.pesanan.find({'username': username}))
    serums = {str(serum['_id']): serum for serum in db.serum.find()}

    return render_template('pesanan.html', pesanan_list=pesanan_list, serums=serums)

#/ --> Dashboard
@app.route('/dashboard',methods=['GET','POST'])
def dashboard():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']

            admin = db.admin.find_one({'username': username})
            if not admin:
                return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

            serum = list(db.serum.find({}))
            return render_template('dashboard.html', serum=serum, username=username)
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
    
    return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

#/ --> IndexA
@app.route('/serum',methods=['GET','POST'])
def serum():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']

            admin = db.admin.find_one({'username': username})
            if not admin:
                return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
            
            serum = list(db.serum.find({}))
            return render_template('indexA.html', serum=serum, username=username)
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
    
    return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

#/ --> Search
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        cari = request.form['cari']
    else:
        cari = request.args.get('cari')
    serum = list(db.serum.find({"nama": {"$regex": f".*{cari}.*", "$options": "i"}}))
    return render_template('index.html', serum=serum)

#/ --> AddSerum
@app.route('/addSerum', methods=['GET', 'POST'])
def addSerum():
    if request.method == 'POST':
        nama_serum = request.form['nama_serum']
        harga = int(request.form['harga'])
        kategori = request.form['kategori']
        deskripsi = request.form['deskripsi']
        nama_gambar = request.files['gambar']

        if nama_gambar:
            nama_file_asli = nama_gambar.filename
            nama_file_gambar = nama_file_asli.split('/')[-1]
            file_path = f'static/images/{nama_file_gambar}'
            nama_gambar.save(file_path)
        else:
            nama_gambar = None

        doc = {
            'nama_serum': nama_serum,
            'harga': harga,
            'kategori': kategori,
            'deskripsi': deskripsi,
            'gambar': nama_file_gambar
        }

        db.serum.insert_one(doc)
        return redirect(url_for("serum"))
    return render_template('addSerum.html')

#/ --> EditSerum
@app.route('/edit/<_id>',methods=['GET','POST'])
def edit(_id):
    if request.method == 'POST':
        id = request.form['id']
        nama_serum = request.form['nama_serum']
        harga = int(request.form['harga'])
        kategori = request.form['kategori']
        deskripsi = request.form['deskripsi']
        nama_gambar = request.files['gambar']

        doc = {
            'nama' : nama_serum,
            'harga' : harga,
            'kategori' : kategori,
            'deskripsi' : deskripsi
        }

        if nama_gambar:
            nama_file_asli = nama_gambar.filename
            nama_file_gambar = nama_file_asli.split('/')[-1]
            file_path = f'static/images/{nama_file_gambar}'
            nama_gambar.save(file_path)
            doc['gambar'] = nama_file_gambar

        db.serum.update_one({'_id': ObjectId(id)}, {'$set': doc})
        return redirect(url_for("serum"))

    id = ObjectId(_id)
    data = list(db.serum.find({'_id': id}))
    return render_template('editSerum.html', data=data)

#/ --> EditSerum (Delete)
@app.route('/delete/<_id>',methods=['GET','POST'])
def delete(_id):
    db.serum.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for("serum"))

#/ --> Data Transaksi
@app.route('/transaksiadm',methods=['GET','POST'])
def pengguna():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']

            admin = db.admin.find_one({'username': username})
            if not admin:
                return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
            
            pengguna = list(db.transaksi.find())
            serums = {str(serum['_id']): serum for serum in db.serum.find()}
            return render_template('user.html', users=pengguna, serums=serums, username=username)
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
    
    return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

#/ --> Data Pesanan
@app.route('/pesananadm', methods=['GET'])
def pesananadm():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']

            admin = db.admin.find_one({'username': username})
            if not admin:
                return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
            
            pesanan = list(db.pesanan.find())
            serums = {str(serum['_id']): serum for serum in db.serum.find()}
            return render_template('pesananadm.html', users=pesanan, serums=serums, username=username)
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
    
    return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

@app.route('/editPesanan/<_id>', methods=['GET', 'POST'])
def editPesanan(_id):
    if request.method == 'POST':
        id = request.form['id']
        username = request.form['username']
        nama = request.form['nama']
        jasa_kirim = request.form['jasa_kirim']
        nomor_resi = request.form['nomor_resi']
        keterangan = request.form['keterangan']

        doc = {
            'username': username,
            'nama': nama,
            'jasa_kirim': jasa_kirim,
            'nomor_resi': nomor_resi,
            'keterangan': keterangan
        }

        db.pesanan.update_one({'_id': ObjectId(id)}, {'$set': doc})
        return redirect(url_for("pesananadm"))

    id = ObjectId(_id)
    data = db.pesanan.find_one({'_id': id})
    
    if data:
        serum_data = db.serum.find_one({'_id': ObjectId(data['serum_id'])})
        nama_serum = serum_data['nama_serum'] if serum_data else "Serum tidak ditemukan"
        data['nama_serum'] = nama_serum
    else:
        data = {}

    return render_template('editPesanan.html', data=data)

#/ --> EditPesanan (Delete)
@app.route('/deletePesanan/<_id>',methods=['GET','POST'])
def deletePesanan(_id):
    db.pesanan.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for("pesananadm"))

#/ --> Kategori Serum
@app.route('/kategoriadm',methods=['GET','POST'])
def kategoriadm():
    token = request.cookies.get(TOKEN_KEY)
    username = None
    
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            username = payload['id']

            admin = db.admin.find_one({'username': username})
            if not admin:
                return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
            kategori = list(db.kategori.find({}))
            return render_template('kategoriAdm.html', kategori=kategori, username=username)
        except jwt.ExpiredSignatureError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))
    
    return redirect(url_for('masukA', msg='There+was+a+problem+logging+you+in'))

#/ --> Tambah Kategori
@app.route('/tmbhKategori', methods=['GET', 'POST'])
def tmbhKategori():
    if request.method == 'POST':
        kategori_serum = request.form['kategori_serum']
        deskripsi_kategori = request.form['deskripsi']
        route = request.form['route']
        nama_gambar = request.files['gambar']

        if nama_gambar:
            nama_file_asli = nama_gambar.filename
            nama_file_gambar = nama_file_asli.split('/')[-1]
            file_path = f'static/images/{nama_file_gambar}'
            nama_gambar.save(file_path)
        else:
            nama_gambar = None

        doc = {
            'kategori_serum': kategori_serum,
            'deskripsi_kategori': deskripsi_kategori,
            'gambar': nama_file_gambar,
            'route': route
        }

        db.kategori.insert_one(doc)
        return redirect(url_for("kategoriadm"))
    return render_template('addKategori.html')

#/ --> EditKategori
@app.route('/editKategori/<_id>', methods=['GET', 'POST'])
def editKategori(_id):
    if request.method == 'POST':
        id = request.form['id']
        kategori_serum = request.form['kategori_serum']
        deskripsi_kategori = request.form['deskripsi']
        route = request.form['route']
        gambar = request.files['gambar']

        doc = {
            'kategori_serum': kategori_serum,
            'deskripsi_kategori': deskripsi_kategori,
            'route': route
        }

        if gambar:
            filename = secure_filename(gambar.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            gambar.save(file_path)
            doc['gambar'] = filename

        db.kategori.update_one({'_id': ObjectId(id)}, {'$set': doc})
        return redirect(url_for("kategoriadm"))

    id = ObjectId(_id)
    data = db.kategori.find_one({'_id': id})
    return render_template('editKategori.html', data=data)

#/ --> EditKategori (Delete)
@app.route('/deleteKategori/<_id>',methods=['GET','POST'])
def deleteKategori(_id):
    db.kategori.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for("kategoriadm"))

if __name__ == '__main__':
    app.run('0.0.0.0',port=5000,debug=True)