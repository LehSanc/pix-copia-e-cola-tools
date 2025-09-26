import pyqrcode
import re
import os

def gerar_qr_code_arquivo(pixcopiaecola, pasta="qrcodes"):

    if not pixcopiaecola:
        print("Nenhum dado fornecido para gerar QR Code")
        return

    try:
        # Remove espaços
        pixcopiaecola = pixcopiaecola.strip()

        # Cria a pasta se não existir
        os.makedirs(pasta, exist_ok=True)

        # Cria um nome de arquivo seguro a partir do pixcopiaecola
        nome_base = re.sub(r'[^a-zA-Z0-9]', '_', pixcopiaecola)  # substitui caracteres inválidos
        nome_arquivo = f'{pasta}/{nome_base}.png'

        # Gera o QR Code
        qr = pyqrcode.create(pixcopiaecola, encoding='utf-8')

        # Salva diretamente no disco
        qr.png(nome_arquivo, scale=8)
        print(f'QR Code salvo em: {nome_arquivo}')

    except Exception as e:
        print(f'Erro ao gerar QR Code: {e}')
