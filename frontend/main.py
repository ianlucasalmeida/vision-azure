from app import create_app

app = create_app()

if __name__ == '__main__':
    # Em um ambiente de produção real, o gunicorn chama 'main:app',
    # então esta seção 'run' é principalmente para testes locais.
    app.run(host='0.0.0.0', port=8000)