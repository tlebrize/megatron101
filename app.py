import sqlite3, os
from flask import Flask, g, request
app = Flask(__name__)
from users import users

###########################################################
#                          DATABASE                       #
###########################################################

DATABASE = os.getcwd() + '/megatron.sl3.db'
TOKEN = os.environ.get('SLACK_TOKEN')
MAX_VOTES = 5

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def exec_db(query, args=()):
    db = get_db()
    db.cursor().execute(query, args)
    db.commit()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

###########################################################
#                         VOTE                            #
###########################################################

def cheat(user, uid):
    q = 'SELECT COUNT(*) FROM vote WHERE user LIKE ? AND uid NOT LIKE ?'
    return query_db(q, args=(user, uid), one=True)[0] > 0

def duplicates(user, target):
    q = 'SELECT COUNT(*) FROM vote WHERE user LIKE ? AND target LIKE ?'
    return query_db(q, args=(user, target), one=True)[0] > 0

def too_many(user, target):
    q = 'SELECT COUNT(*) FROM vote WHERE user LIKE ?'
    return query_db(q, args=(user,), one=True)[0] > MAX_VOTES

@app.route('/vote', methods=['POST'])
def slack_vote():
    if request.form.get('token') != 'K1X5hQbImLWIeoNLIiqRzS46':
        print 'UNAUTHORIZED'
        return 'UNAUTHORIZED'
    user = request.form.get('user_name')
    target = request.form.get('text', '').split(' ')[0]
    uid = request.form.get('user_id', '')
    if target not in users:
        return 'Wut ? :eggplant:'
    if user == target:
        return 'Lmao :sadpanda:'
    if cheat(user, uid):
        print 'CHEAT', user, uid, target
        return 'Passe au bocal stp. :facepalm:'
    if duplicates(user, target):
        return 'You ca\'nt vote twice for the same student. :busts_in_silhouette:'
    if too_many(user, target):
        return 'You\'ve spent all your votes. :dealwithitparrot:'
    votes_left = 'SELECT COUNT(*) FROM vote WHERE user LIKE ?'
    exec_db('INSERT INTO vote VALUES (?,?,?)', args=(uid, user, target))
    count = query_db(votes_left, args=(user,), one=True)[0]
    return '{} vote(s) left. :shuffleparrot:'.format(MAX_VOTES - count)

@app.route('/list', methods=['POST'])
def slack_list():
    if request.form.get('token') != 'K1X5hQbImLWIeoNLIiqRzS46':
        print 'UNAUTHORIZED'
        return 'UNAUTHORIZED'
    user = request.form.get('user_name')
    user_votes = 'SELECT target FROM vote WHERE user LIKE ?'
    rows = query_db(user_votes, args=(user,))
    return ', '.join([r['target'] for r in rows]) + ' :aw_yeah:'

@app.route('/results', methods=['GET'])
def results():
    count_votes = 'SELECT COUNT(*) FROM vote WHERE target LIKE ?'
    return '\n'.join(['<p>{}: {}</p>'.format(user, query_db(count_votes,
        args=(user,), one=True)[0]) for user in users])



