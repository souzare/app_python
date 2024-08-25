from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import os
from datadog import initialize, statsd

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post

# Configurações do Datadog
options = {
    'statsd_host': 'ip-172-31-9-121.ec2.internal',  # ou o host onde seu agente Datadog está rodando
    'statsd_port': 8125
}
initialize(**options)

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    
    # Incrementar o contador de requisições
    statsd.increment('http.requests.total')
    
    # Monitorar o número atual de posts
    statsd.gauge('posts.count', len(posts))
    
    # Medir a latência
    with statsd.timed('http.request.duration'):
        return render_template('index.html')

@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)

@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                         ' WHERE id = ?',
                         (title, content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)

@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))

@app.route('/error')
def error():
    # Simulate a 500 Internal Server Error
    statsd.increment('http.request.errors', tags=["error_type:500"])
    return "Internal Server Error", 500

@app.route('/notfound')
def not_found():
    # Simulate a 404 Not Found Error
    statsd.increment('http.request.errors', tags=["error_type:404"])
    return "Not Found", 404

app.run(host='0.0.0.0', port=5000)
