import sqlalchemy
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import current_user, login_required
from core.scraper import Scraper
from core.models import User, Book, Author, db, Bookshelf, Review, PopularBook
from core.forms import Login, SearchBooks, ChallengeForm, NewShelf
from datetime import datetime
from sqlalchemy import func

main = Blueprint('main', __name__)


@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    challenge_form = ChallengeForm(obj=current_user)
    page = request.args.get('page', 1, type=int)

    if db.session.query(PopularBook).filter(
            sqlalchemy.extract('month', PopularBook.date_added) == datetime.now().month).first():
        popular_books = db.session.query(PopularBook).all()
    else:
        scraper = Scraper()
        popular_books = scraper.get_new_releases()
    data = {'date': datetime.now(),
            'popular_books': popular_books[:12],
            'challenge_completed': current_user.get_challenge_status(),
            'challenge_status': current_user.get_challenge_progress(),
            'currently_reading': current_user.get_random_books('Currently Reading', 5),
            'current_year_books': current_user.books_read_this_year(),
            'new_reviews': Review.query.order_by(db.desc(Review.date_created)).paginate(page=page, per_page=7),
            }


    return render_template('index.html', challenge_form=challenge_form, data=data)


@main.route('/update_challenge', methods=['POST'])
def update_challenge():
    next_url = request.form.get('next_url')
    if ChallengeForm(request.form).cancel_challenge.data:
        current_user.challenge = None
        db.session.commit()
    elif ChallengeForm(request.form).validate_on_submit():
        current_user.challenge = int(request.form.get('challenge'))
        db.session.commit()
    return redirect(next_url)

@main.route('/search', methods=['POST', 'GET'])
def search():
    to_read_shelf = current_user.get_shelf('Want to Read')

    if request.method == 'POST':
        search_query = request.form.get('query')
    else:
        search_query= request.args.get('query')

    scraper = Scraper()
    search_results = scraper.get_search_results(search_query)

    return render_template('search.html', query=search_query, search_results=search_results, to_read_shelf=to_read_shelf)


@main.route('/book_view/<goodreads_id>', methods=['GET', 'POST'])
def book_view(goodreads_id):
    book = Book.query.filter(Book.goodreads_id == goodreads_id).first()
    if not book:
        scraper = Scraper()
        book = scraper.get_book_details(goodreads_id)
        book.save_to_db()

    own_review = db.session.query(Review).filter(Review.book == book, Review.user == current_user).first()
    other_reviews = db.session.query(Review).filter(Review.book == book, Review.user != current_user).all()



    if request.method == 'POST':
        next_url = request.form.get('next_url')

        if 'update-review' in request.form:
            current_user.add_review(book, request.form.get('review-body'))
            return redirect(next_url)

        elif 'delete-review' in request.form:
            current_user.delete_review(book)
            return redirect(next_url)

    return render_template('book_view.html', book=book, own_review=own_review, other_reviews=other_reviews)


@main.route('/rate_book/<book_title>', methods=['POST'])
def rate_book(book_title):
    rating = request.form.get('rating-value')
    next_url = request.form.get('next-url')
    current_user.rate_book(book_title, rating)
    return redirect(next_url)


@main.route('/reading_list/<selected_bookshelf_name>', methods=['GET', 'POST'])
@login_required
def reading_lists(selected_bookshelf_name):
    new_shelf_form = NewShelf()
    challenge_form = ChallengeForm(obj=current_user)

    bookshelf = Bookshelf.query.filter(
        Bookshelf.user_id == current_user.id).filter(
        Bookshelf.name == selected_bookshelf_name).first()
    books_with_ratings = db.session.query(Book, func.coalesce(Review.rating, 0)).filter(
        Book.id.in_([x.id for x in bookshelf.books])).join(Review, isouter=True).all()
    print(books_with_ratings)
    data = {
        'year': datetime.now().year,
        # 'currently_reading': db.session.query(Bookshelf).filter(Bookshelf.name=='Currently Reading').first().books,

        'challenge_completed': current_user.get_challenge_status(),
        'challenge_status': current_user.get_challenge_progress(),
        'current_year_books': current_user.books_read_this_year(),
    }


    if new_shelf_form.validate_on_submit():
        shelf_name = new_shelf_form.shelf_input.data
        new_bookshelf = Bookshelf(name=shelf_name, user=current_user)
        db.session.add(new_bookshelf)
        db.session.commit()
        return redirect(url_for('main.reading_lists', selected_bookshelf_name=new_bookshelf.name))

    return render_template('reading_lists.html',
                           new_shelf_form=new_shelf_form,
                           challenge_form = challenge_form,
                           selected_bookshelf=bookshelf,
                           data=data,
                           # default_bookshelves=current_user.get_default_bookshelves(),
                           books_with_ratings=books_with_ratings)




@main.route('/remove_bookshelf/', methods=['POST'])
def delete_bookshelf():
    next_url = request.form.get('next_url')
    selected_bookshelf_name = request.form.get('selected_bookshelf_name')
    current_user.remove_bookshelf(selected_bookshelf_name)
    return redirect(next_url)
    # return redirect(url_for('main.reading_lists', selected_bookshelf_name='Read'))


@main.route('/remove_book/<bookshelf_name>/<goodreads_id>', methods=['POST'])
def remove_from_bookshelf(bookshelf_name, goodreads_id):
    next_url = request.form.get('next_url')
    book = Book.query.filter(Book.goodreads_id == goodreads_id).first()
    bookshelf = Bookshelf.query.filter(
        Bookshelf.user_id == current_user.id).filter(Bookshelf.name == bookshelf_name).first()
    bookshelf.books.remove(book)
    db.session.commit()
    return redirect(next_url)


@main.route('/add_book/<bookshelf_name>/<goodreads_id>', methods=['POST'])
def add_to_bookshelf(bookshelf_name, goodreads_id):
    next_url = request.form.get('next_url')

    book = Book.query.filter(Book.goodreads_id == goodreads_id).first()
    if not book:
        scraper = Scraper()
        book = scraper.get_book_details(goodreads_id)

    bookshelf = Bookshelf.query.filter(
        Bookshelf.user_id == current_user.id).filter(Bookshelf.name == bookshelf_name).first()

    bookshelf.books.append(book)
    db.session.commit()

    return redirect(next_url)

@main.route('/ReadingChallenge', methods=['GET', 'POST'])
def reading_challenge():
    challenge_form = ChallengeForm(obj=current_user)
    data = {
        'year': datetime.now().year,
        'challenge_completed': current_user.get_challenge_status(),
        'challenge_status': current_user.get_challenge_progress(),
        'current_year_books': current_user.books_read_this_year(),
    }
    return render_template('challenge.html', data=data, form=challenge_form)

@main.route('/book_error')
def book_error(goodreads_id):
    return render_template('err.html')
