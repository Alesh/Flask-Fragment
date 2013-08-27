from flask import Flask
from flask.ext.script import Manager
from flask.ext.fragment import Fragment
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
app = Flask(__name__)
db = SQLAlchemy(app)
login = LoginManager(app)
fragment = Fragment(app)
manager = Manager(app, with_default_commands=False)



### Views ###
from models import User, Post, Comment, LoginForm, RegisterForm, PostForm, CommentForm
from flask.ext.login import current_user, login_required, login_user, logout_user
from flask import render_template, redirect, url_for, request, flash

PAGE_SIZE = 20

@app.errorhandler(404)
def page_not_found(e):
    return render_template('page404.html'), 404

@app.route('/')
@app.route('/posts/<page>', endpoint='posts')
def index(page=None):
    page = int(page or 1)
    return render_template('index.html', page=page)
                           

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db.session.add(form.user)
        db.session.commit()
        login_user(form.user)
        flash('You are registered successfully.', 'info')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/post/<id>', methods=['GET', 'POST'])
def post_with_comments(id):
    form=CommentForm()
    post=Post.query.filter_by(id=id).first()
    if (post and form.validate_on_submit()
             and current_user.is_authenticated()):
        form.comment.author_id = current_user.id
        form.comment.post_id = post.id
        db.session.add(form.comment)
        db.session.commit()
        flash('Your comment has saved successfully.', 'info')
        # reset cache
        fragment.reset('user_info', current_user.id)
        pagination = Post.query.filter_by().paginate(1, PAGE_SIZE)
        for N in range(1, pagination.pages+1):
            fragment.reset('post_list', N)
        return redirect(url_for('post_with_comments', id=id))
    return render_template('post_with_comments.html', post=post, form=form)
    
@app.route('/add', methods=['GET', 'POST'])
@login_required
def post_add():
    form = PostForm()
    if form.validate_on_submit():
        form.post.author_id = current_user.id
        db.session.add(form.post)
        db.session.commit()
        flash('Your post has saved successfully.', 'info')
        # reset cache
        fragment.reset('user_info', current_user.id)
        pagination = Post.query.filter_by().paginate(1, PAGE_SIZE)
        for N in range(1, pagination.pages+1):
            fragment.reset('post_list', N)
        return redirect(url_for('index'))
    return render_template('post_add.html', form=form)

### Fragments ###

@app.fragment()
def login_form():
    return render_template('login.html', form=LoginForm())

@app.fragment(timeout=300)
def user_info(userid):
    return render_template('userinfo.html')

@app.fragment(timeout=300)
def post_list(page):
    pagination = Post.query.filter_by().paginate(page, PAGE_SIZE)
    posts = Post.query.filter_by().offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE).all()
    return render_template('post_list.html', pagination=pagination, posts=posts)
    
    
    
### Security ###

@login.user_loader
def load_user(userid):
    return User.get(userid)

@login.unauthorized_handler
def unauthorized():
    flash('Only authorized users can add posts.', 'warning')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user)
        flash('You are logged successfully.', 'info')
        return redirect(request.args.get('next') or url_for('index'))
    return redirect(url_for('index'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))




### Config ###
class DefaultConfig(object):
    FRAGMENT_CACHING = True
    SECRET_KEY = 'Development_Secret_Key_Must_Be_Overwritten'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ssiblog.db'



### Console command ###
import os.path

@manager.command
def debug():
    """Runs application within debug environment."""
    from flask_debugtoolbar import DebugToolbarExtension
    app.config['DEBUG'] = True
    DebugToolbarExtension(app)
    app.run(debug=True)

@manager.command
def nginx_conf():
    """Creates application config for nginx."""
    file_name = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nginx.conf')
    fragment._create_nginx_config(file_name)
    

@manager.command
def create_db():
    """Creates application DB."""
    from models import DB
    url = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite://')
    if url.startswith('sqlite:////'):
        path = url[10:]
        if not os.path.exists(path):
            os.makedirs(path)
    DB.create_all()
    DB.session.commit()
    

if __name__ == '__main__':
    app.config.from_object(DefaultConfig)
    manager.run()
    