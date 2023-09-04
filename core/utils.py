from core.models import User, Book
from flask import session

def add_url(url):
    session['selected_book_url'] = url