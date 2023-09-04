from core import create_app




if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='192.168.0.148', port='5000')

    