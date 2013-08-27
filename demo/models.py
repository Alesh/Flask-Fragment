## Models ###
import flask
from flask.ext.login import UserMixin
from flask.ext.sqlalchemy import SQLAlchemy
DB = SQLAlchemy()

class Comment(DB.Model):
    id = DB.Column(DB.Integer(), primary_key=True, autoincrement=True)
    author_id = DB.Column(DB.Integer, DB.ForeignKey('user.id'))
    post_id = DB.Column(DB.Integer, DB.ForeignKey('post.id'))
    created_at = DB.Column(DB.DateTime(), default=DB.func.now())
    body = DB.Column(DB.Text())

class Post(DB.Model):
    id = DB.Column(DB.Integer(), primary_key=True, autoincrement=True)
    author_id = DB.Column(DB.Integer, DB.ForeignKey('user.id'))
    created_at = DB.Column(DB.DateTime(), default=DB.func.now())
    title = DB.Column(DB.String(128))
    body = DB.Column(DB.Text())
    comments = DB.relationship('Comment', backref='post', lazy='dynamic')

    comments_count = DB.column_property(
        DB.select([DB.func.count(Comment.id)]).where(Comment.post_id==id), deferred=True)

class User(DB.Model, UserMixin):
    id = DB.Column(DB.Integer(), primary_key=True, autoincrement=True)
    username = DB.Column(DB.String(32), unique=True)
    password = DB.Column(DB.String(32))
    posts = DB.relationship('Post', backref='author', lazy='dynamic')
    comments = DB.relationship('Comment', backref='author', lazy='dynamic')

    posts_count = DB.column_property(
        DB.select([DB.func.count(Post.id)]).where(Post.author_id==id), deferred=True)

    comments_count = DB.column_property(
        DB.select([DB.func.count(Comment.id)]).where(Comment.author_id==id), deferred=True)
    
    @classmethod
    def get(cls, id):
        return cls.query.filter_by(id=id).first()
    
    def get_id(self):
        return unicode(self.id)
        


### Forms ###
from flask_wtf import Form as BaseForm
from wtforms import HiddenField, TextField, TextAreaField, PasswordField, validators

class Form(BaseForm):
    def _flash_error_except(self, *fields):
        for key. errors in self.errors:
            if key not in ('body','title'):
                for error in errors:
                    flask.flash(error, 'error') 
        

class LoginForm(Form):
    next = HiddenField()
    username = TextField('Username')
    password = PasswordField('Password')
    
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)    
    
    def validate(self):
        if not super(LoginForm, self).validate():
            self._flash_error_except('username', 'password')
            return False
        self.user = User.query.filter_by(username=self.username.data, password=self.password.data).first()
        if self.user is None:
            flask.flash('Username or password incorrect.', 'error')
            return False
        return True


class RegisterForm(Form):
    username = TextField('Username', [validators.InputRequired(),
                                      validators.Length(min=2, max=32)])
    password = PasswordField('Password', [validators.InputRequired(),
                                          validators.Length(min=6, max=32)])
    repassword = PasswordField('Confirm', [validators.InputRequired(),
                                           validators.EqualTo('password')])

    def __init__(self, *args, **kwargs):
        self.user = None
        super(RegisterForm, self).__init__(*args, **kwargs)    

    def validate(self):
        if not super(RegisterForm, self).validate():
            self._flash_error_except('username', 'password', 'repassword')
            return False
        if User.query.filter_by(username=self.username.data).first():
            flask.flash('User with the same name already registered.', 'error')
            return False
        self.user = User(username=self.username.data, password=self.password.data)
        return True


class PostForm(Form):
    title = TextField('Title', [validators.InputRequired(),
                                      validators.Length(min=2, max=128)])
    body = TextAreaField('Body', [validators.InputRequired(),
                                      validators.Length(min=2, max=2048)])

    def validate(self):
        if not super(PostForm, self).validate():
            self._flash_error_except('body','title')
            return False
        self.post = Post(title=self.title.data, body=self.body.data)
        return True


class CommentForm(Form):
    body = TextAreaField('Body', [validators.InputRequired(),
                                      validators.Length(min=2, max=2048)])
    def validate(self):
        if not super(CommentForm, self).validate():
            self._flash_error_except('body')
            return False
        self.comment = Comment(body=self.body.data)
        return True
