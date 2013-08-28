from flask import Flask
from flask.ext.fragment import Fragment
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
app = Flask(__name__)
db = SQLAlchemy(app)
fragment = Fragment(app)
login = LoginManager(app)

from models import User, Post, Comment, LoginForm, RegisterForm, PostForm, CommentForm
from flask.ext.login import current_user, login_required, login_user, logout_user
from flask import render_template, redirect, url_for, request, flash


#### VIEWS
from models import User, Post, Comment, LoginForm, RegisterForm, PostForm, CommentForm
from flask.ext.login import current_user, login_required, login_user, logout_user
from flask import render_template, redirect, url_for, request, flash

POSTS_ON_PAGE = 20
COMMENTS_ON_PAGE = 20


## Handlers

@login.user_loader
def load_user(userid):
    return User.get(userid)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('page404.html'), 404

@login.unauthorized_handler
def unauthorized():
    flash('Only authorized users can do requested action or see requested page.', 'warning')
    return redirect(url_for('index'))


### Login/Logout/Register pages

@fragment(app)
def login_form():
    return render_template('login.html', form=LoginForm())

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


### Index page

@fragment(app, cache=300)
def user_info(userid):
    return render_template('fragments/userinfo.html')


@fragment(app, cache=300)
def posts_list(page):
    page = int(page)
    page_size = POSTS_ON_PAGE
    pagination = Post.query.filter_by().paginate(page, page_size)
    posts = Post.query.filter_by().offset((page-1)*page_size).limit(page_size).all()
    return render_template('fragments/posts_list.html', pagination=pagination, posts=posts)


@fragment.resethandler(posts_list)
def reset_posts_list():
    page_size = POSTS_ON_PAGE
    pagination = Post.query.filter_by().paginate(1, page_size)
    for N in range(pagination.pages):
        fragment.reset_url(url_for('posts_list', page=N+1))


@app.route('/posts/<int:page>')
@app.route('/', endpoint='index', defaults={'page':1})
def posts(page):
    return render_template('index.html', page=page)


### Post page

@fragment(app, cache=300)
def post_show(post_id):
    post = Post.query.filter_by(id=post_id).first()
    return render_template('fragments/post_show.html', post=post)


@fragment(app, cache=300)
def comments_list(post_id, page):
    page = int(page)
    page_size = COMMENTS_ON_PAGE
    pagination = Comment.query.filter_by(post_id=post_id).paginate(page, page_size)
    comments = Comment.query.filter_by(post_id=post_id).offset((page-1)*page_size).limit(page_size).all()
    return render_template('fragments/comments_list.html', post_id=post_id, page=page,
                                                           pagination=pagination, comments=comments)


@fragment.resethandler(comments_list)
def reset_comments_list(post_id):
    page_size = COMMENTS_ON_PAGE
    pagination = Comment.query.filter_by(post_id=post_id).paginate(1, page_size)
    for N in range(pagination.pages):
        fragment.reset_url(url_for('comments_list', post_id=post_id, page=N+1))


@app.route('/post/<int:post_id>/<int:page>', methods=['GET', 'POST'])
def post(post_id, page):
    form = CommentForm()
    if (current_user.is_authenticated() and form.validate_on_submit()):
        form.comment.author_id = current_user.id
        form.comment.post_id = post_id
        db.session.add(form.comment)
        db.session.commit()
        fragment.reset(posts_list)
        fragment.reset(comments_list, post_id)
        fragment.reset(user_info, current_user.id)
        flash('Your comment has saved successfully.', 'info')
    return render_template('post.html', form=form, post_id=post_id, page=page)


### New Post page

@app.route('/new/post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        form.post.author_id = current_user.id
        db.session.add(form.post)
        db.session.commit()
        fragment.reset(posts_list)
        fragment.reset(user_info, current_user.id)
        flash('Your post has saved successfully.', 'info')
        return redirect(url_for('index'))
    return render_template('newpost.html', form=form)


### Config ###

class DefaultConfig(object):
    FRAGMENT_CACHING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ssiblog.db'
    SECRET_KEY = 'Development_Secret_Key_Must_Be_Overwritten'
    

### Console command ###

import sys
import os.path
PY2 = sys.version_info[0] == 2

from flask.ext.script import Manager
manager = Manager(app, with_default_commands=False)

@manager.command
def debug():
    """Runs application within debug environment."""
    app.config['DEBUG'] = True
    if PY2:
        from flask_debugtoolbar import DebugToolbarExtension
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
