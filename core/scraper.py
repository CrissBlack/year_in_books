from bs4 import BeautifulSoup
import requests
from core.models import Book, Author, PopularBook
import json
from datetime import datetime
from requests_html import HTMLSession
import os



base_url = 'https://www.goodreads.com'
search_suffix = '/search?q='
HEADERS = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64)'
                       'AppleWebKit/537.36 (KHTML, like Gecko)'
                       'Chrome/44.0.2403.157 Safari/537.36'),
        'Accept-Language': 'en-US, en;q=0.5'
    }

# class SearchResultItem:
#     def __init__(self, goodreads_id, cover_thumb_url, title=None, author_list=None):
#         self.goodreads_id = goodreads_id
#         self.cover_thumb_url = cover_thumb_url
#         self.title = title
#         self.author_list = author_list
#


class Scraper:
    def __init__(self):
        self.base_url = base_url
        self.search_suffix = search_suffix

    def get_search_results(self, query):
        url = self.base_url + self.search_suffix + query.replace(' ', '+')
        html = requests.get(url=url, headers=HEADERS)
        soup = BeautifulSoup(html.text, features='lxml')

        search_results = []
        books_table = soup.select('table[class="tableList"] > tr')

        for result in books_table:
            goodreads_id = result.select_one('input[name="book_id"]').get('value')
            found_book = Book.query.filter(Book.goodreads_id==goodreads_id).first()
            if found_book:
                search_results.append(found_book)
            else:
                book = Book(goodreads_id=goodreads_id, title=result.select_one('a[class="bookTitle"]').text,
                            cover_url=result.select_one('img[class="bookCover"]').get('src'))

                author_list = [name.text for name in result.select('a[class="authorName"] span[itemprop="name"]')]
                for author in author_list:
                    book.authors.append(Author(name=author))
                search_results.append(book)




        return search_results



    def get_book_details(self, goodreads_id):
        book_url = f'{self.base_url}/book/show/{goodreads_id}'
        soup = BeautifulSoup(requests.get(book_url, headers=HEADERS).text, features='lxml')

        book_title = soup.select_one('.Text__title1').text
        book_cover_url = soup.select_one('.BookCover__image img').get('src')
        book_description = soup.select_one('.BookPageMetadataSection__description span').text

        features = soup.select_one('.FeaturedDetails').text.split(',')
        book_pages = features[0] if len(features) > 2 else 0

        book = Book(goodreads_id=goodreads_id, title=book_title, pages=book_pages, description=book_description,
                    cover_url=book_cover_url)
        authors = [x.text for x in soup.select('.ContributorLinksList a')]

        for name in authors:
            db_author = Author.query.filter(Author.name == name).first()
            if db_author:
                book.authors.append(db_author)
            else:
                book.authors.append(Author(name=name))

        return book

    @staticmethod
    def get_new_releases():
        url = 'https://www.goodreads.com/genres/new-releases'
        resp = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, features='lxml')

        new_releases = []
        releases_html = soup.select('div[class="coverWrapper"]')
        for release in releases_html:

            cover_url = release.select_one("img").get('src')
            goodreads_id = os.path.basename(cover_url).split('.')[0]
            title = release.select_one("img").get('alt')
            if 'blank' not in goodreads_id:

                new_release = PopularBook(goodreads_id=goodreads_id, title=title, cover_url=cover_url)
                new_release.save_to_db()
                new_releases.append(new_release)

        return new_releases

