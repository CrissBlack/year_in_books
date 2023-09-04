from datetime import datetime
from typing import Type
import sqlalchemy
import sqlalchemy.exc
from sqlalchemy.sql import func
from flask import flash
from core import db, login_manager
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

import math

book_author = db.Table(
    'book_authors',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id', ondelete="CASCADE")),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id', ondelete="CASCADE"))
)




class BookBookshelf(db.Model):
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), primary_key=True)
    bookshelf_id = db.Column(db.Integer, db.ForeignKey('bookshelf.id', ondelete="CASCADE"), primary_key=True)




class Review(db.Model):
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    book_id = db.Column('book_id', db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), primary_key=True)
    rating = db.Column(db.Integer, default=None)
    content = db.Column(db.String(2000))
    date_created = db.Column('date_created', db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = db.relationship('User', backref='reviews', passive_deletes=True)
    book = db.relationship('Book', backref='reviews', passive_deletes=True)



    @staticmethod
    def get_new_reviews(count):
        new_reviews = db.session.query(Review).order_by(db.desc(Review.date_created)).limit(count).all()

        return new_reviews


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(30), nullable=True, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    challenge = db.Column(db.Integer, nullable=True)
    bookshelves = db.relationship('Bookshelf', backref='user')

    def __repr__(self):
        return f'User: {self.username}'

    def delete_review(self, book):
        """
        Sets user's review content for the selected book to an empty string. Does not affect rating.
        :param book: Book object
        """
        review = db.session.query(Review).filter(
            Review.user == self, Review.book == book).first()
        review.content = ''
        db.session.commit()

    def add_review(self, book: 'Book', review_body: str):
        """
        Adds or updates a review content for the selected book. Does not affect rating.
        :param book: Book object
        :param review_body: String. Review content
        :return:
        """
        old_review = db.session.query(Review).filter(Review.book == book, Review.user == current_user).first()
        if old_review:
            old_review.content = review_body
            db.session.commit()
        else:
            review = Review(user=self, book=book, content=review_body)
            db.session.add(review)
            db.session.commit()

    def get_challenge_status(self):
        if self.challenge:
            return self.challenge <= len(self.get_shelf('Read').books)

    def get_challenge_progress(self):
        if self.challenge:
            per_month_goal = self.challenge / 12
            current_month = datetime.now().month
            should_have_read = per_month_goal * current_month

            challenge_status = len(self.get_shelf('Read').books) - should_have_read
            return math.ceil(challenge_status)

    def add_default_bookshelves(self):
        default_shelves_names = ['Currently Reading', 'Read', 'Want to Read']
        for shelf_name in default_shelves_names:
            db.session.add(Bookshelf(name=shelf_name, user=self, is_custom=False))
            db.session.commit()

    def books_read_this_year(self):
        current_year = datetime.now().year
        read_shelf = self.get_shelf('Read')

        book_list = Book.query.filter(
            Book.id.in_([book.id for book in read_shelf.books]), sqlalchemy.extract('year', Book.date_added) == current_year).all()

        return book_list

    def get_shelf(self, name):
        found_shelf = Bookshelf.query.filter(Bookshelf.user_id == self.id).filter(Bookshelf.name == name).first()

        return found_shelf

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # def get_default_bookshelves(self):
    #     return [self.get_shelf(x) for x in ['Read', 'Currently Reading', 'Want to Read']]

    def get_custom_bookshelves(self):
        return [shelf for shelf in self.bookshelves if shelf not in self.get_default_bookshelves()]

    def get_random_books(self, bookshelf_name, count):
        bookshelf = Bookshelf.query.filter(
            Bookshelf.user_id == self.id).filter(Bookshelf.name == bookshelf_name).first()

        if bookshelf.books:
            return bookshelf.books[:count]
        else:
            return None

    def remove_bookshelf(self, name):
        selected_bookshelf = Bookshelf.query.filter(
            Bookshelf.user_id == self.id).filter(Bookshelf.name == name).first()
        db.session.delete(selected_bookshelf)
        db.session.commit()

    def rate_book(self, book_title, rating):
        book = Book.query.filter(Book.title == book_title).first()
        old_review = Review.query.filter(Review.user_id == self.id).filter(Review.book_id == book.id).first()

        if old_review:
            old_review.rating = rating
            db.session.commit()
        else:
            review = Review(user=current_user, book=book, rating=rating)
            db.session.add(review)
            db.session.commit()

    # def to_json(self):
    #     return dict(id=self.id, username=self.username, email=self.email, password_hash=self.password_hash,
    #                 challenge=self.challenge,
    #                 bookshelves=[x.name for x in self.bookshelves])


class Bookshelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"))
    is_custom = db.Column(db.Boolean, default=True)

    books = db.relationship('Book', secondary='book_bookshelf', backref='bookshelves')




class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goodreads_id = db.Column(db.String(20), unique=True)
    title = db.Column(db.String(30), nullable=False)
    pages = db.Column(db.Integer)
    description = db.Column(db.String(500))
    cover_url = db.Column(db.String(100))
    cover_path = db.Column(db.String(50))
    date_added = db.Column('date_added', db.DateTime(timezone=True), default=func.now())

    authors = db.relationship('Author', secondary=book_author, backref='books')

    def __repr__(self):
        return self.title

    def save_to_db(self):
        if not Book.query.filter(Book == self).first():
            self.download_cover()
            db.session.add(self)
            db.session.commit()

    def download_cover(self):
        img_data = requests.get(url=self.cover_url).content
        img_name = self.cover_url.split("/")[-1]
        save_path = f'core/static/img/covers/{img_name}'
        with open(save_path, 'wb') as handler:
            handler.write(img_data)
        self.cover_path = f'img/covers/{img_name}'


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f'Author: {self.name}'


class PopularBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    cover_path = db.Column(db.String(50))
    cover_url = db.Column(db.String(100))
    goodreads_id = db.Column(db.String(25))
    date_added = db.Column(db.DateTime(timezone=True), default=func.now())

    def download_cover(self):
        img_data = requests.get(url=self.cover_url).content
        img_name = self.cover_url.split("/")[-1]
        save_path = f'core/static/img/covers/{img_name}'
        with open(save_path, 'wb') as handler:
            handler.write(img_data)
        self.cover_path = f'img/covers/{img_name}'
        db.session.commit()

    def save_to_db(self):
        if not PopularBook.query.filter(PopularBook == self).first():
            self.download_cover()
            db.session.add(self)
            db.session.commit()

@login_manager.user_loader
def load_user(user):
    return User.query.get(user)
